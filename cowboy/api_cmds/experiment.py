from cowboy.http import APIClient
from cowboy.db.core import Database

from typing import List

db = Database()
api = APIClient(db)


### stopped here
def api_experiment(
    repo_name: str,
    test_modules: List[str],
):
    """
    Augments existing test modules with new test cases
    """
    pass
    #
    # response = api.long_post(
    #     "/test-gen/augment",
    #     {
    #         "src_file": src_file,
    #         "repo_name": repo_name,
    #         "mode": mode,
    #         "tms": tms,
    #     },
    # )

    # return response
