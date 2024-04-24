from dataclasses import dataclass
from typing import Any, List, Optional

from src.db.core import Database


@dataclass
class RepoConfig:
    repo_name: str  # of form owner_repo
    url: str
    forked_url: str  # URL pointing to our forked repo
    cloned_folders: List[
        str
    ]  # list of cloned folders used for parallelizing run_test; many to many relationship
    # with instantiated repo contexts
    source_folder: (
        str  # source folder used for read/temp write operations; one to many relations
    )

    # pytest specific confs (although they could be generally applicable)
    python_conf: "PythonConf"

    def serialize(self):
        return {
            "repo_name": self.repo_name,
            "url": self.url,
            "forked_url": self.forked_url,
            "cloned_folders": self.cloned_folders,
            "source_folder": self.source_folder,
            "python_conf": self.python_conf.__dict__,
        }


@dataclass
class PythonConf:
    cov_folders: List[str]
    test_folder: str
    interp: str
    pythonpath: str

    def get(self, __name: str, default: Any) -> Any:
        return self.__dict__.get(__name, default)


class RepoConfigRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, repo_config: RepoConfig):
        self.db.save_dict(key="repos", value=repo_config.serialize())

    def find(self, repo_name: str) -> Optional[RepoConfig]:
        repo_config = self.db.get(repo_name)
        if repo_config:
            return self.rcfg_from_dict(repo_config)

        return None

    def rcfg_from_dict(self, d: dict) -> RepoConfig:
        python_conf = PythonConf(**d["python_conf"])
        return RepoConfig(
            repo_name=d["repo_name"],
            url=d["url"],
            forked_url=d["forked_url"],
            cloned_folders=d.get("cloned_folders", []),
            source_folder=d.get("source_folder", []),
            python_conf=python_conf,
        )
