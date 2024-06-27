from pathlib import Path
import os
import click
import sys
import shutil
import subprocess
from git import Repo

from cowboy.db.core import Database
from cowboy.utils import gen_random_name

from cowboy.repo.models import RepoConfig
from cowboy.config import REPO_ROOT
from cowboy.exceptions import CowboyClientError

ALL_REPO_CONF = "src/config"
NUM_CLONES = 2


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


def create_cloned_folders(
    repo_conf: RepoConfig, repo_root: Path, db: Database, num_clones: int
):
    """
    Clones the repo from the forked_url
    """
    cloned_folders = []
    repo = db.get(repo_conf.repo_name)
    if repo:
        click.secho("Repo already exists", fg="red")
        sys.exit()

    clone_dir = repo_root / repo_conf.repo_name
    if clone_dir.exists():
        click.secho(
            f"Cloned folder {str(repo_root / repo_conf.repo_name)} already exist, skipping creating anew ...",
            fg="green",
        )
        return [str(f) for f in clone_dir.iterdir() if f.is_dir()]

    for i in range(num_clones):
        cloned_path = clone_repo(clone_dir, repo_conf.url)
        setuppy_init(repo_conf.repo_name, cloned_path, repo_conf.python_conf.interp)

        cloned_folders.append(str(cloned_path))

    return cloned_folders


def get_cloned_folders(repo_name: str):
    """
    Returns the cloned_folders for a repo
    """
    repo_folder = Path(REPO_ROOT) / repo_name
    if not repo_folder.exists():
        raise CowboyClientError(f"Repo {repo_name} does not exist")

    return [f for f in repo_folder.iterdir() if f.is_dir()]


# TODO: here there may be errors
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
    # if stderr:
    #     print("Error while setup.py install")
    #     print(stderr)


def clone_repo(clone_dir: Path, repo_url: str) -> Path:
    """
    Creates a clone of the repo locally
    """
    dest_folder = clone_dir / gen_random_name()
    if dest_folder.exists():
        os.makedirs(dest_folder)

    Repo.clone_from(repo_url, dest_folder)

    return dest_folder


def delete_cloned_folders(repo_root: Path, repo_name: str):
    """
    Deletes cloned folders
    """
    try:
        repo_path = repo_root / repo_name
        shutil.rmtree(repo_path, onerror=del_file)
    except FileNotFoundError:
        return
