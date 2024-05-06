import threading
import time

from src.config import TASK_ENDPOINT

from src.repo.runner import PytestDiffRunner
from src.http.base import APIClient
from src.db.core import Database
from src.repo.models import RepoConfig, RepoConfigRepository

from concurrent.futures import ThreadPoolExecutor

from cowboy_lib.api.runner.shared import RunTestTaskClient

import json


class RunTestClient:
    def __init__(
        self,
        rconf_repo: RepoConfigRepository,
        api_client: APIClient,
        fetch_endpoint: str,
        # task_complete: str,
        sleep_interval=5,
    ):
        self.rconf_repo = rconf_repo
        self.run_executor = ThreadPoolExecutor(max_workers=5)
        self.api_client = api_client
        self.fetch_endpoint = fetch_endpoint

        # retrieved tasks
        self.retrieved_t = []
        self.start_t = []

        self.poll_server()

    def get_runner(self, repo_name: str) -> PytestDiffRunner:
        """
        Returns runner for repo_name
        """
        repo_conf = self.rconf_repo.find(repo_name)
        return PytestDiffRunner(repo_conf)

    def fetch_tasks_thread(self):
        """
        Fetches task from server, single thread
        """
        task_res = self.api_client.get("/task/get")
        if task_res:
            for t in task_res:
                print(t)
                task = RunTestTaskClient(**t, **t["task_args"])
                print("Task: ", task)
                threading.Thread(target=self.run_task_thread, args=(task,)).start()

    def run_task_thread(self, task: RunTestTaskClient):
        """
        Runs task fetched from server, launched for every new task
        """
        runner = self.get_runner(task.repo_name)
        cov_res, *_ = runner.run_test(task.task_args)
        result_task = task
        result_task.result = cov_res.to_dict()

        # Note: need json() vs dict(), cuz json() actually converts nested objects, unlike dict
        self.api_client.post(f"/task/complete", json.loads(result_task.json()))

    def poll_server(self):
        while True:
            fetch_tasks = threading.Thread(target=self.fetch_tasks_thread, daemon=True)
            fetch_tasks.start()

            time.sleep(1.0)  # Poll every 'interval' second


if __name__ == "__main__":
    db = Database()
    api = APIClient(db)
    rconf_repo = RepoConfigRepository(db)

    RunTestClient(rconf_repo, api, TASK_ENDPOINT)
