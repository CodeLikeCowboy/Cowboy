from dataclasses import dataclass
from typing import Any, List, Optional
from pathlib import Path

from src.db.core import Database
from src.exceptions import CowboyConfigError
from uuid import uuid4


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

    def __post_init__(self):
        self.python_conf = PythonConf(**self.python_conf)

    def serialize(self):
        return {
            "repo_name": self.repo_name,
            "url": self.url,
            "forked_url": self.forked_url,
            "cloned_folders": self.cloned_folders,
            "source_folder": self.source_folder,
            "python_conf": self.python_conf.__dict__,
        }


# TODO:
# consider adding more arguments from pytest here
@dataclass
class PythonConf:
    cov_folders: List[str]
    test_folder: str
    interp: str
    pythonpath: str

    # ghetto AF, we should just be using pydantic for this
    def __post_init__(self):
        mandatory_keys = ["cov_folders", "interp"]
        for k in self.__dict__:
            if k not in mandatory_keys:
                continue

            v = getattr(self, k)
            if not v:
                raise CowboyConfigError(f"{k} must be set in config")


class RepoConfigRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, repo_config: RepoConfig):
        self.db.save_dict(
            dict_key="repos", key=repo_config.repo_name, value=repo_config.serialize()
        )

    def delete(self, repo_name: str):
        self.db.delete_dict("repos", repo_name)

    def find(self, repo_name: str) -> Optional[RepoConfig]:
        repo_config = self.db.get_dict("repos", repo_name)
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
