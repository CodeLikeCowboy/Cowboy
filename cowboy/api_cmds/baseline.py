from cowboy.http import APIClient
from cowboy.db.core import Database


db = Database()
api = APIClient(db)


def api_baseline(repo_name):
    api.long_post(
        f"/tm/baseline",
        {
            "repo_name": repo_name,
            "test_modules": [
                "TestWoodpecker",
                # "test_codecov_cli.py",
                # "TestUploadCollectionResultFile",
                # "TestRunners",
                # "TestLabelAnalysisRequestResult",
            ],
        },
    )
