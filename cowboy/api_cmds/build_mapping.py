from cowboy.http import APIClient
from cowboy.db.core import Database


db = Database()
api = APIClient(db)


def api_baseline(repo_name, mode, tms):
    """
    Builds the test module to source file mapping for each selected
    test module
    """
    api.long_post(
        "/tm/build-mapping",
        {
            "repo_name": repo_name,
            "mode": mode,
            "tms": tms,
            "files": [],
            # TODO: change this to False
            "overwrite": True,
        },
    )
