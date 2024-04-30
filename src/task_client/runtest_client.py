import threading
import time
from queue import Queue
import requests

from src.config import TASK_ENDPOINT

from src.repo.runner import PytestDiffRunner
from src.shared.models import RunnerTask
from src.http.base import APIClient
from src.db.core import Database
from src.repo.models import RepoConfig, RepoConfigRepository

from concurrent.futures import ThreadPoolExecutor


class RunTestClient:
    def __init__(
        self,
        runner: PytestDiffRunner,
        api_client: APIClient,
        fetch_endpoint: str,
        # task_complete: str,
        sleep_interval=5,
    ):
        self.runner = runner
        self.run_executor = ThreadPoolExecutor(max_workers=5)
        self.api_client = api_client
        self.fetch_endpoint = fetch_endpoint

        # retrieved tasks
        self.retrieved_t = []
        self.start_t = []

        self.poll_server()

    def fetch_tasks_thread(self):
        """
        Fetches task from server, single thread
        """
        task_res = self.api_client.get("/task/get")
        if task_res:
            for t in task_res:
                task = RunnerTask(**t)
                threading.Thread(target=self.run_task_thread, args=(task,)).start()

    def run_task_thread(self, task: RunnerTask):
        """
        Runs task fetched from server, launched for every new task
        """

        cov_res, *_ = self.runner.run_test(**task.args)

        result_task = task
        result_task.result = cov_res.to_dict()

        print("Sending task from client: ", result_task.__dict__)

        self.api_client.post(f"/task/complete", result_task.__dict__)

    def poll_server(self):
        while True:
            fetch_tasks = threading.Thread(target=self.fetch_tasks_thread, daemon=True)
            fetch_tasks.start()

            time.sleep(1.0)  # Poll every 'interval' second


if __name__ == "__main__":
    db = Database()
    api = APIClient(db)
    repo_conf = RepoConfigRepository(db).find("codecov-cli")
    runner = PytestDiffRunner(repo_conf)

    RunTestClient(runner, api, TASK_ENDPOINT)
