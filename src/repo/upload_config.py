from .models import RepoConfigRepository
from .models import RepoConfig, PythonConf
from src.db.core import Database


from typing import Tuple, Dict

db = Database()


# /add/repo_config
# TODO: implement /delete/repo_config -> for example, when we want to
# delete existing config. Should only do it through this method because
# we want to trigger the corresponding folder creation steps in RepoFactory
def owner_name_from_url(url: str) -> Tuple[str, str]:
    owner, repo_name = url.split("/")[-2:]
    return owner, repo_name


def save_repo_config(settings: Dict):
    rc_repo = RepoConfigRepository(db)
    owner, repo_name = owner_name_from_url(settings["url"])

    py_conf = PythonConf(
        cov_folders=settings.get("cov_folders", []),
        test_folder=settings.get("test_folder", ""),
        interp=settings.get("interp", ""),
        pythonpath=settings.get("pythonpath", ""),
    )

    repo_config = RepoConfig(
        repo_name=owner + "_" + repo_name,
        url=settings.get("url"),
        forked_url="",
        cloned_folders=[],
        source_folder="",
        py_confg=py_conf,
    )

    rc_repo.save(repo_config)


if __name__ == "__main__":
    for repo in [
        "requests",
        "fastapi-users",
        "trio",
        "textual",
        "fastapi",
        "codecov-cli",
    ]:
        save_repo_config(app_config[repo])
