from typing import List, Optional

from pydantic import BaseModel, validator
from cowboy.db.core import Database


class PythonConf(BaseModel):
    cov_folders: List[str]
    interp: str
    test_folder: Optional[str]
    pythonpath: Optional[str]

    @validator("interp")
    def validate_interp(cls, v):
        import os

        if not os.path.exists(v):
            raise ValueError(f"Interpreter path {v} does not exist")
        return v


class RepoConfig(BaseModel):
    repo_name: str  # of form owner_repo
    url: str
    cloned_folders: List[
        str
    ]  # list of cloned folders used for parallelizing run_test; many to many relationship
    # with instantiated repo contexts
    source_folder: (
        str  # source folder used for read/temp write operations; one to many relations
    )
    # pytest specific confs (although they could be generally applicable)
    python_conf: "PythonConf"
    is_experiment: Optional[bool] = False

    @validator("url")
    def validate_url(cls, v):
        import re

        if not re.match(r"^https:\/\/github\.com\/[\w-]+\/[\w-]+(\.git)?$", v):
            raise ValueError(
                "URL must be a valid GitHub HTTPS URL and may end with .git"
            )
        # if v.endswith(".git"):
        #     raise ValueError("URL should not end with .git")
        if re.match(r"^git@github\.com:[\w-]+\/[\w-]+\.git$", v):
            raise ValueError("SSH URL format is not allowed")
        return v

    def __post_init__(self):
        if isinstance(self.python_conf, dict):
            self.python_conf = PythonConf(**self.python_conf)

    def serialize(self):
        return {
            "repo_name": self.repo_name,
            "url": self.url,
            "cloned_folders": self.cloned_folders,
            "source_folder": self.source_folder,
            "python_conf": self.python_conf.__dict__,
            "is_experiment": self.is_experiment,
        }


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
            cloned_folders=d.get("cloned_folders", []),
            source_folder=d.get("source_folder", []),
            python_conf=python_conf,
        )
