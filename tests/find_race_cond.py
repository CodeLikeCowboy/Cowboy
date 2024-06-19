from cowboy.runner.python import PytestDiffRunner
from cowboy_lib.api.runner.shared import RunTestTaskArgs
from cowboy.http import APIClient
from cowboy.db.core import Database
from cowboy.repo.models import RepoConfig

import threading
from concurrent.futures import ThreadPoolExecutor

if __name__ == "__main__":
    db = Database()
    api = APIClient(db)
    repo_config = RepoConfig(**api.get(f"/repo/get/test3"))

    # Initialize PytestDiffRunner
    runner = PytestDiffRunner(repo_config)

    # Setup RunTestTaskArgs
    task_args = RunTestTaskArgs(patch_file=None, exclude_tests=[], include_tests=[])

    round = 0
    while True:
        from datetime import datetime

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("STARTING ROUND: ", round, "AT TIME: ", current_time)

        def run_fake_test():
            print("Running fake test suite")
            runner.fake_test_suite(task_args)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_fake_test) for _ in range(5)]
            for future in futures:
                future.result()

        round += 1
