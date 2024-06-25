from cowboy_lib.repo.repository import PatchFileContext, GitRepo
from cowboy_lib.coverage import CoverageResult
from cowboy_lib.api.runner.shared import RunTestTaskArgs, FunctionArg
from cowboy.repo.models import RepoConfig
from cowboy.exceptions import CowboyClientError
from cowboy.logger import task_log

from .base import RunnerError, TestSuiteError

import os
import subprocess
from typing import List, Tuple, NewType, Dict
import json
import hashlib
from pathlib import Path


COVERAGE_FILE = "coverage.json"
TestError = NewType("TestError", str)


class DiffFileCreation(Exception):
    pass


def hash_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def hash_file(filepath):
    """Compute SHA-256 hash of the specified file"""
    with open(filepath, "r", encoding="utf-8") as f:
        buf = f.read()

    return hash_str(buf)


def hash_coverage_inputs(directory: Path, cmd_str: str) -> str:
    """Compute SHA-256 for the curr dir and cmd_str"""
    hashes = []
    for f in directory.iterdir():
        if f.is_file() and f.name.endswith(".py"):
            file_hash = hash_file(f)
            hashes.append((str(f), file_hash))

    # Sort based on file path and then combine the file hashes
    hashes.sort()
    combined_hash = hashlib.sha256()
    for _, file_hash in hashes:
        combined_hash.update(file_hash.encode())

    combined_hash.update(cmd_str.encode())
    return combined_hash.hexdigest()


from contextlib import contextmanager
import queue


class LockedRepos:
    """
    A list of available repos for concurrent run_test invocations, managed as a FIFO queue
    """

    def __init__(self, path_n_git: List[Tuple[Path, GitRepo]]):
        self.capacity = len(path_n_git)
        self.queue = queue.Queue()
        for item in path_n_git:
            self.queue.put(item)

    @contextmanager
    def acquire_one(self) -> Tuple[Path, GitRepo]:
        path, git_repo = self.queue.get()  # This will block if the queue is empty

        task_log.info(f"Acquired repo: {path}")
        try:
            yield (path, git_repo)
        finally:
            self.release((path, git_repo))

            task_log.info(f"Released repo: {path}")

    def release(self, path_n_git: Tuple[Path, GitRepo]):
        self.queue.put(path_n_git)  # Return the repo back to the queue

    def __len__(self):
        return self.queue.qsize()


def get_exclude_path(
    func: FunctionArg,
    rel_fp: Path,
):
    """
    Converts a Function path
    """
    excl_name = (
        (func.name.split(".")[0] + "::" + func.name.split(".")[1])
        if func.is_meth
        else func.name
    )

    # need to do this on windows
    return str(rel_fp).replace("\\", "/") + "::" + excl_name


class PytestDiffRunner:
    """
    Executes the test suite before and after a diff is applied,
    and compares the results. Runs in two modes: full and selective.
    In full mode, the full test suite is run.
    In selective mode, only selected test cases.
    """

    def __init__(
        self,
        # assume to be a test file for now
        repo_conf: RepoConfig,
        test_suite: str = "",
    ):
        self.src_folder = Path(repo_conf.source_folder)
        self.test_folder = Path(repo_conf.python_conf.test_folder)
        self.interpreter = Path(repo_conf.python_conf.interp)
        self.python_path = Path(repo_conf.python_conf.pythonpath)

        if not self.interpreter.exists():
            raise RunnerError(f"Runtime path {self.interpreter} does not exist")

        missing = self.check_missing_deps(self.interpreter)
        if missing:
            raise RunnerError(f"{missing}")

        self.cloned_folders = [Path(p) for p in repo_conf.cloned_folders]
        self.cov_folders = [Path(p) for p in repo_conf.python_conf.cov_folders]

        self.test_repos = LockedRepos(
            list(
                zip(
                    self.cloned_folders,
                    [GitRepo(Path(p)) for p in repo_conf.cloned_folders],
                )
            )
        )
        if len(self.test_repos) == 0:
            raise CowboyClientError("No cloned repos created, perhaps run init again?")

        self.test_suite = test_suite

    def check_missing_deps(self, interp) -> List[bool]:
        """
        Check if test depdencies are installed in the interpreter
        """
        installed = []
        deps = ["pytest-cov", "pytest"]
        try:
            for dep in deps:
                result = subprocess.run(
                    [interp, "-m", "pip", "show", dep],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    installed.append((dep, False))
                else:
                    installed.append((dep, True))

        except (subprocess.CalledProcessError, FileNotFoundError):
            installed.append((dep, False))

        msg = (
            f"The following deps are not installed: {[d[0] for d in installed if not d[1]]}"
            if installed
            else ""
        )
        return msg

    def verify_clone_dirs(self, cloned_dirs: List[Path]):
        """
        Verifies that the hash of all *.py files are the same for each cloned dir
        """
        import hashlib

        hashes = []
        for clone in cloned_dirs:
            f_buf = ""
            for py_file in clone.glob("test*.py"):
                with open(py_file, "r") as f:
                    f_buf += f.read()

            f_buf_hash = hashlib.md5(f_buf.encode()).hexdigest()
            hashes.append(f_buf_hash)

        if any(h != hashes[0] for h in hashes):
            raise CowboyClientError("Cloned directories are not the same")

    def set_test_repos(self, repo_paths: List[Path]):
        self.test_repos = LockedRepos(
            list(zip(repo_paths, [GitRepo(p) for p in repo_paths]))
        )

        self.verify_clone_dirs(repo_paths)

    def _get_exclude_tests_arg_str(
        self, excluded_tests: List[Tuple[FunctionArg, Path]], cloned_path: Path
    ):
        """
        Convert the excluded tests into Pytest deselect args
        """
        if not excluded_tests:
            return ""

        # PATCH: just concatenate the path with base folder
        tranf_paths = []
        for test, test_fp in excluded_tests:
            tranf_paths.append(get_exclude_path(test, test_fp))

        return "--deselect=" + " --deselect=".join(tranf_paths)

    def _get_include_tests_arg_str(self, include_tests: []):
        if not include_tests:
            return ""

        arg_str = ""
        AND = " and"
        for test in include_tests:
            arg_str += f"{test}{AND}"

        arg_str = arg_str[: -len(AND)]
        # return "-k " + '"' + arg_str + '"'
        return "-k " + arg_str

    def _construct_cmd(
        self, repo_path, selected_tests: str = "", deselected_tests: str = ""
    ):
        """
        Constructs the cmdstr for running pytest
        """

        cmd = [
            "cd",
            str(repo_path),
            "&&",
            str(self.interpreter),
            "-m",
            "pytest",
            str(self.test_folder),
            "--tb",
            "short",
            selected_tests,
            deselected_tests,
            # "-v",
            "--color",
            "no",
            f"--cov={'--cov='.join([str(folder) + ' ' for folder in self.cov_folders])}",
            "--cov-report",
            "json",
            "--cov-report",
            "term",
            "--continue-on-collection-errors",
            "--disable-warnings",
        ]

        return " ".join(cmd)

    def run_testsuite(self, args: RunTestTaskArgs) -> Tuple[CoverageResult, str, str]:
        with self.test_repos.acquire_one() as repo_inst:
            cloned_path, git_repo = repo_inst

            patch_file = args.patch_file
            if patch_file:
                patch_file.path = cloned_path / patch_file.path
                task_log.info(f"Using patch file: {patch_file.path}")

            exclude_tests = args.exclude_tests
            include_tests = args.include_tests

            env = os.environ.copy()
            if self.python_path:
                env["PYTHONPATH"] = self.python_path

            exclude_tests = self._get_exclude_tests_arg_str(exclude_tests, cloned_path)
            include_tests = self._get_include_tests_arg_str(include_tests)
            cmd_str = self._construct_cmd(cloned_path, include_tests, exclude_tests)

            task_log.info(f"Running with command: {cmd_str}")

            with PatchFileContext(git_repo, patch_file):
                proc = subprocess.Popen(
                    cmd_str,
                    # env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True,
                )
                stdout, stderr = proc.communicate()

                # raise exception only no coverage
                try:
                    with open(cloned_path / COVERAGE_FILE, "r") as f:
                        coverage_json = json.loads(f.read())
                        cov = CoverageResult(stdout, stderr, coverage_json)
                        if not cov.coverage:
                            print("No coverage!")
                            raise Exception()
                except Exception:
                    raise TestSuiteError(stderr, str(cloned_path), cmd_str)

        return (
            cov,
            stdout,
            stderr,
        )

    # NOTE: keep this around, there is still that race condition bug we need
    # to find
    # def fake_test_suite(self, args: RunTestTaskArgs) -> Tuple[CoverageResult, str, str]:
    #     import time
    #     import random

    #     with self.test_repos.acquire_one() as repo_inst:
    #         print(f"Acquired repo: {repo_inst}")
    #         cloned_path, git_repo = repo_inst

    #         patch_file = args.patch_file
    #         if patch_file:
    #             patch_file.path = cloned_path / patch_file.path
    #             task_log.info(f"Using patch file: {patch_file.path}")

    #         exclude_tests = args.exclude_tests
    #         include_tests = args.include_tests

    #         env = os.environ.copy()
    #         if self.python_path:
    #             env["PYTHONPATH"] = self.python_path

    #         exclude_tests = self._get_exclude_tests_arg_str(exclude_tests, cloned_path)
    #         include_tests = self._get_include_tests_arg_str(include_tests)
    #         cmd_str = self._construct_cmd(cloned_path, include_tests, exclude_tests)
    #         print(f"Running with command: {cmd_str}")

    #         with PatchFileContext(git_repo, patch_file):
    #             time.sleep(random.randint(1, 10))
    #             # proc = subprocess.Popen(
    #             #     cmd_str,
    #             #     # env=env,
    #             #     stdout=subprocess.PIPE,
    #             #     stderr=subprocess.PIPE,
    #             #     shell=True,
    #             #     text=True,
    #             # )
    #             # stdout, stderr = proc.communicate()
    #             # if stderr:
    #             #     raise TestSuiteError(stderr)

    #             # # read pycoverage result
    #             # with open(cloned_path / COVERAGE_FILE, "r") as f:
    #             #     coverage_json = json.loads(f.read())
    #             #     cov = CoverageResult(stdout, stderr, coverage_json)

    #     return (
    #         None,
    #         "",
    #         "",
    #     )
