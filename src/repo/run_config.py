from logging import getLogger
from subprocess import Popen, PIPE
from pathlib import Path
from typing import Any, List, Dict
from enum import Enum, auto

import re
from shutil import copyfile, SameFileError

from src.utils import RepoPath

runc_logger = getLogger("run_config")
logger = getLogger("test_results")


class DepsManager(Enum):
    PIPENV = auto()
    POETRY = auto()
    SETUP_PY = auto()
    REQUIREMENTS_TXT = auto()
    UNKNOWN = auto()


class EmptyDict:
    """
    An empty dictionary
    """

    def __get__(self, instance, owner):
        return {}

    def get(self, value, default):
        return default


class RepoRunConfig:
    """
    Holds repo specific configurations required to execute tests.
    Reads user defined config from settings folder, and tries to resolve to sane defaults
    """

    def __init__(self, repo_path: RepoPath, settings: Dict):
        self.repo_path = repo_path

        runc_logger.info(f"Initializing repo: {repo_path}")
        if not self.repo_path.exists():
            # test suite may be renamed or deleted
            raise Exception(f"GitRepo does not exist: {repo_path}")

        self.repo_name = self.repo_path.name
        self.repoconf_folder = settings.get("repoconf_folder", "")
        # self._write_coveragerc_file()

        self.url = settings.get("url", None)
        # defaults to the main folder of the repo
        self.src_folder: Path = self.repo_path / settings.get("src_folder", "")
        # NOTE: root folder from which test coverage is collected
        # should also be where tests are held
        self.test_folder: Path = self.repo_path / settings.get("test_folder", "tests")
        # cov folders passed to pycov "-cov" parameter
        self.cov_folders: List[Path] = [
            Path(p) for p in settings.get("cov_folders", ["."])
        ]
        python_path = settings.get("python_path", None)
        self.python_path: str = python_path if python_path else None

        # probably also want to move to factory
        # try to resolve the interpreter
        interp = settings.get("interp", None)
        if interp:
            self.interp = Path(interp)
        else:
            self.interp = self._find_default_interp_path()

        self.settings_folder: str = ""

    def _write_coveragerc_file(self):
        try:
            copyfile(
                self.repoconf_folder / ".coveragerc",
                self.repo_path / ".coveragerc",
            )
        except SameFileError:
            pass
        except FileNotFoundError:
            logger.warning("No .coveragerc file found ..")
