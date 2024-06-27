from cowboy.http import APIClient
from cowboy.db.core import Database


db = Database()
api = APIClient(db)


def api_get_head(repo_name):
    """
    Gets all test_modules for a given repo
    """
    commit = api.get(f"/repo/get_head/{repo_name}")

    return commit["sha"]
