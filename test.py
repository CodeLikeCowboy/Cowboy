import requests
from typing import Tuple, List, Optional
import time
from logging import getLogger
import os

from dataclasses import dataclass, field
from pathlib import Path
from git import Repo
from git import Diff

from cowboy_lib.repo.repository import GitRepo

# is this the right way? Feel like proper way is to load config
# at single point upstream and then pass it down .. but idk

# from dotenv import load_dotenv

# load_dotenv()
# GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

logger = getLogger("test_results")


def parse_git_url(git_url: str):
    """
    Parses the GitHub URL to extract the owner and repository name.

    Parameters:
    - git_url: The full GitHub repository URL.

    Returns:
    A tuple containing the owner and repository name.
    """
    parts = git_url.split("/")
    owner = parts[-2]
    repo_name = parts[-1].split(".git")[0]
    return owner, repo_name


if __name__ == "__main__":
    repo = GitRepo(Path("test_forks/forked_offset_finder"))

    with open("test_forks/forked_offset_finder/test4.py", "w") as f:
        f.write("print('hello world')")

    merge_url = repo.checkout_and_push("test_branch", "testing commit", ["test4.py"])

    # delete_forked = GithubAPI.delete_fork(forked_url)
    # if delete_forked:
    #     print("Successfully deleted forked repo")
