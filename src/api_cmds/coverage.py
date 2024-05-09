from src.http import APIClient
from src.db.core import Database


db = Database()
api = APIClient(db)


def api_coverage(repo_name):
    api.get(f"/coverage/{repo_name}")
