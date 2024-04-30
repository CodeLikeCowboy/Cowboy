from dataclasses import dataclass
from logging import getLogger, config as loggerConfig
from pathlib import Path
from collections import defaultdict
import uuid
import os

import shutil
import subprocess
from git import Repo

from src.db.core import Database
from src.utils import gen_random_name

from src.repo.models import RepoConfig
from src.repo.runner import PytestDiffRunner

logger = getLogger("test_results")
longterm_logger = getLogger("longterm")

ALL_REPO_CONF = "src/config"
NUM_CLONES = 2


# TODO: have to check if windows or linux
def del_file(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    import stat

    # Is the error an access error?
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


# TODO: make this into factory constructor
# so we dont have to import all this shit
class RepoTestContext:
    def __init__(
        self,
        repo_conf: RepoConfig,
        db_conn: Database,
        verify: bool = False,
    ):
        self.repo_path = repo_conf.cloned_folders[0]
        self.db_conn = db_conn

        # TODO: support injecting this argument
        self.runner = PytestDiffRunner(repo_conf)

        if verify:
            test_results = self.test_run()

    def test_run(self):
        base_cov, stdout, stderr = self.runner.run_test()
        if stderr:
            logger.info(f"Error running test => STDERR:\n{stderr}")

        return base_cov


def create_repo(repo_conf: RepoConfig, repo_root: Path, num_clones: int):
    """
    Clones the repo from the forked_url
    """
    if len(repo_conf.cloned_folders) < num_clones:
        for i in range(num_clones - len(repo_conf.cloned_folders)):
            # TODO: we need to change
            cloned_path = clone_repo(repo_root, repo_conf.url, repo_conf.repo_name)
            setuppy_init(repo_conf.repo_name, cloned_path, repo_conf.python_conf.interp)

            repo_conf.cloned_folders.append(str(cloned_path))

    return repo_conf


def setuppy_init(repo_name: str, cloned_path: Path, interp: str):
    """
    Initialize setup.py file for each interpreter
    """
    cmd = ["cd", str(cloned_path), "&&", interp, "setup.py", "install"]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True,
    )

    stdout, stderr = proc.communicate()
    if stderr:
        logger.warn(f"Error initializing setup.py for {repo_name}:\n{stderr}")


def clone_repo(repo_root: Path, repo_url: str, repo_name: str) -> Path:
    """
    Creates a clone of the repo locally
    """
    dest_folder = repo_root / repo_name / gen_random_name()
    if dest_folder.exists():
        os.makedirs(dest_folder)

    Repo.clone_from(repo_url, dest_folder)

    return dest_folder


def delete_repo(repo_root: Path, repo_name: str):
    """
    Deletes a repo from the db and all its cloned folders
    """
    repo_path = repo_root / repo_name
    shutil.rmtree(repo_path, onerror=del_file)
