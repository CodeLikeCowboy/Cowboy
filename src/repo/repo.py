from dataclasses import dataclass
from logging import getLogger, config as loggerConfig
from pathlib import Path
from collections import defaultdict
import uuid
import os

import subprocess
from typing import Optional, Tuple, List, Dict
from git import Repo

from src.db.core import Database
from src.utils import gen_random_name

from src.repo.models import RepoConfig, PythonConf, RepoConfigRepository
from src.repo.runner import PytestDiffRunner

logger = getLogger("test_results")
longterm_logger = getLogger("longterm")

ALL_REPO_CONF = "src/config"
NUM_CLONES = 2
BASE_PATH = Path("repos")


# TODO: make this into factory constructor
# so we dont have to import all this shit
class RepoTestContext:
    def __init__(
        self,
        repo_path: Path,
        repo_name: str,
        repo_conf: RepoConfig,
        db_conn: Database,
        cloned_paths: List[Path] = [],
        config_logger: bool = True,
        log_debug: bool = False,
        verify: bool = False,
        num_repos: int = 1,
        cloned_dirs: List[Path] = [],
    ):
        # experiment id for tracking different runs
        self.exp_id = str(uuid.uuid4())[:8]
        # if config_logger:
        #     ConfigureLogger(repo_name, job_id=self.exp_id, log_debug=log_debug)

        self.repo_path = repo_path
        self.db_conn = db_conn

        # BACKWARDS COMPAT: remove when unnessescary
        if not cloned_dirs:
            cloned_dirs = [repo_path]

        # TODO: support injecting this argument
        self.runner = PytestDiffRunner(repo_conf)

        if verify:
            test_results = self.test_run()

    def test_run(self):
        base_cov, stdout, stderr = self.runner.run_test()
        if stderr:
            logger.info(f"Error running test => STDERR:\n{stderr}")

        return base_cov


class RepoTestContextFactory:
    """
    Creates creating multiple copies of the same Repo
    """

    def __init__(self, db_conn: Database):
        self.db_conn = db_conn
        self.rc_repo = RepoConfigRepository(db_conn)

        self.cloned_folders: Dict[str, List[Path]] = defaultdict(list)
        self.source_folders: Dict[str, Path] = {}
        self.repo_configs: Dict[str, PythonConf] = {}

    # TODO: move to client
    def initialize_folders(self, repo_name: str):
        """
        Either gets cloned path from config or creates anew
        """
        repo_conf = self.rc_repo.find(repo_name)
        if not repo_conf.source_folder:
            cloned_path = self.clone_repo(repo_conf.url, repo_conf.repo_name)
            repo_conf.source_folder = str(cloned_path)

        if len(repo_conf.cloned_folders) < NUM_CLONES:
            for i in range(NUM_CLONES - len(repo_conf.cloned_folders)):
                cloned_path = self.clone_repo(repo_conf.forked_url, repo_conf.repo_name)
                repo_conf.cloned_folders.append(str(cloned_path))

        self.source_folders[repo_conf.repo_name] = Path(repo_conf.source_folder)
        self.cloned_folders[repo_conf.repo_name] = [
            Path(fp) for fp in repo_conf.cloned_folders
        ]

        self.rc_repo.save(repo_conf)

    def setuppy_init(self, repo_name: str, cloned_path: Path):
        """
        Initialize setup.py file for each interpreter
        """
        interp = self.repo_configs[repo_name].interp
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

    def clone_repo(self, repo_url: str, repo_name: str) -> Path:
        """
        Creates a clone of the repo locally
        """
        dest_folder = BASE_PATH / repo_name / gen_random_name()
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)  # Ensure the destination folder exists

        Repo.clone_from(repo_url, dest_folder)
        self.setuppy_init(repo_name, dest_folder)

        return dest_folder

    def create_context(
        self,
        repo_name: str,
        settings: Dict = {},
        # technically there is nothing special about this folder
        # that sets it apart from the other cloned folders
        repo_path: Path = None,
        config_logger: bool = True,
        log_debug: bool = False,
        verify: bool = False,
    ) -> RepoTestContext:
        """ """
        # BACKWARDS COMPAT: remove when unnessescary
        if not settings:
            r_config = self.repo_configs.get(repo_name, None)
            if not r_config:
                r_config = self.rc_repo.find(repo_name)

            if not r_config:
                raise Exception(
                    f"No such repo {repo_name}. Remember repo names are created in the following format <owner>_<repo_name>"
                )

            self.repo_configs[repo_name] = r_config.python_conf
            if (
                not self.source_folders.get(repo_name, None)
                or not len(self.cloned_folders.get(repo_name, [])) < NUM_CLONES
            ):
                self.initialize_folders(repo_name)

        settings = settings if settings else r_config.python_conf
        repo_path = repo_path if repo_path else self.source_folders[repo_name]

        print("Repo Path: ", repo_path)

        # TODO: replace all repo configuration with persisted config
        repo_ctxt = RepoTestContext(
            repo_path,
            repo_name,
            r_config,
            self.db_conn,
            config_logger=config_logger,
            log_debug=log_debug,
            verify=verify,
            cloned_dirs=self.cloned_folders[repo_name],
        )

        return repo_ctxt
