from cowboy.http import APIClient
from cowboy.db.core import Database

import click

db = Database()
api = APIClient(db)


def api_augment(repo_name: str, mode: str = "auto", src_file: str = "", tms: str = ""):
    """
    Augments existing test modules with new test cases
    """

    response, status = api.long_post(
        "/test-gen/augment",
        {
            "src_file": src_file,
            "repo_name": repo_name,
            "mode": mode,
            "tms": tms,
        },
    )

    return response, status
