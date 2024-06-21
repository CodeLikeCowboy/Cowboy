from cowboy.http import APIClient
from cowboy.db.core import Database
from typing import List

from enum import Enum

db = Database()
api = APIClient(db)


class AugmentTestMode(str, Enum):
    AUTO = "auto"
    FILE = "files"
    TM = "module"
    ALL = "all"


def api_augment(repo_name: str, mode: str = "auto", tms: str = ""):
    """
    Augments existing test modules with new test cases
    """
    if mode not in [e.value for e in AugmentTestMode]:
        raise ValueError(
            f"Invalid mode {mode}, following are allowed: {', '.join(AugmentTestMode.__members__)}"
        )

    response = api.long_post(
        f"/test-gen/augment",
        {
            "repo_name": repo_name,
            "mode": mode,
            "tms": tms,
            "files": [],
        },
    )

    return response["session_id"]
