from git import Repo
from cowboy_lib.repo.diff import CommitDiff
from cowboy_lib.repo import GitRepo

from pathlib import Path

# Example usage
repo_path = r"C:\Users\jpeng\Documents\business\cowboy-test\test-frontend-user\repos\test3\nmopgpuu"


GitRepo(Path(repo_path)).check_for_updates()
