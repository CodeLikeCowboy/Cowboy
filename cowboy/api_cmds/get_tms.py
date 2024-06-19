from cowboy.http import APIClient
from cowboy.db.core import Database


db = Database()
api = APIClient(db)


def api_get_tms(repo_name):
    """
    Gets all test_modules for a given repo
    """
    tms = api.get(f"/tm/{repo_name}")
    return tms
