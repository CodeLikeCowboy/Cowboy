from cowboy.http import APIClient
from cowboy.db.core import Database

from cowboy_lib.coverage import Coverage
from collections import defaultdict

from typing import List, Tuple

db = Database()
api = APIClient(db)


class CovList:
    """
    Contains a list of test modules mapped to coverage
    """

    def __init__(self, tm_covs: List[Tuple[str, Coverage]]):
        self.cov_list = defaultdict(list)

        for tm, cov in tm_covs:
            self.cov_list[tm].append(cov)

    def find(self, filename: str):
        """
        Finds the corresponding TestModules name for a given filename
        """
        tms = []
        for tm, covs in self.cov_list.items():
            if filename in [cov.filename for cov in covs]:
                tms.append(tm)

        return tms

    def print_all(self):
        for tm, covs in self.cov_list.items():
            print("TestModule: ", tm)
            for cov in covs:
                print(cov)


def api_tm_coverage(repo_name):
    """
    Get mapped (tm, coverage) from server. Multiple coverages can be mapped to a single test module
    """
    cov_list, _ = api.get(f"/coverage/sorted/{repo_name}")

    return CovList([(cov[0], Coverage(**cov[1])) for cov in cov_list])
