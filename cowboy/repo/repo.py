from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import os
import click
import sys
import shutil
import subprocess
from git import Repo

from cowboy.db.core import Database
from cowboy.utils import gen_random_name

from cowboy.repo.models import RepoConfig
from cowboy.repo.runner import PytestDiffRunner

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
    print("Cloning repos ...")
    cloned_folders = []
    repo = db.get(repo_conf.repo_name)
    if repo:
        click.secho("Repo already exists", fg="red")
        sys.exit()

    db.save_list("repos", repo_conf.repo_name)
    if len(repo_conf.cloned_folders) < num_clones:
        for i in range(num_clones - len(repo_conf.cloned_folders)):
            cloned_path = clone_repo(repo_root, repo_conf.url, repo_conf.repo_name)
            setuppy_init(repo_conf.repo_name, cloned_path, repo_conf.python_conf.interp)

            cloned_folders.append(str(cloned_path))

    return cloned_folders


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


def clone_repo(repo_root: Path, repo_url: str, repo_name: str) -> Path:
    """
    Creates a clone of the repo locally
    """
    dest_folder = repo_root / repo_name / gen_random_name()
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
