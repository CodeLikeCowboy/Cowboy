from cowboy.http import APIClient
from cowboy.db.core import Database

from enum import Enum

db = Database()
api = APIClient(db)


class AugmentTestMode(str, Enum):
    AUTO = "auto"
    FILE = "file"
    TM = "module"
    ALL = "all"


def api_augment(repo_name: str, mode: str = "auto", src_file: str = "", tms: str = ""):
    """
    Augments existing test modules with new test cases
    """
    if mode not in [e.value for e in AugmentTestMode]:
        raise ValueError(
            f"Invalid mode {mode}, following are allowed: {', '.join(AugmentTestMode.__members__)}"
        )

    response = api.long_post(
        "/test-gen/augment",
        {
            "src_file": src_file,
            "repo_name": repo_name,
            "mode": mode,
            "tms": tms,
        },
    )

    return response["session_id"]
