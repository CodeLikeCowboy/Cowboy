import threading
import time

from cowboy.config import TASK_ENDPOINT
from cowboy.repo.runner import PytestDiffRunner
from cowboy.db.core import Database
from cowboy.repo.models import RepoConfig
from cowboy.http import APIClient

from cowboy_lib.api.runner.shared import RunTestTaskClient

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime
from pathlib import Path


class BGClient:
    """
    Single Task client that runs as a subprocess in the background
    and fetches tasks from server
    """

    def __init__(
        self,
        api_client: APIClient,
        fetch_endpoint: str,
        heart_beat_fp: Path,
        heart_beat_interval: int = 5,
        sleep_interval=5,
    ):
        self.run_executor = ThreadPoolExecutor(max_workers=5)
        self.api_client = api_client
        self.fetch_endpoint = fetch_endpoint

        # each repo has one runner
        self.runners = {}

        # curr tasks : technically dont need since we await every new
        # tasks via runner.acquire_one() but use for debugging
        self.curr_t = []
        self.completed = 0

        # retrieved tasks
        self.lock = Lock()
        self.retrieved_t = []
        self.start_t = []

        # heartbeat
        self.heart_beat_fp = Path(heart_beat_fp)
        self.heart_beat_interval = heart_beat_interval

        # run tasks
        t1 = threading.Thread(target=self.start_heartbeat, daemon=True)
        t2 = threading.Thread(target=self.start_polling, daemon=True)

        t1.start()
        t2.start()

    def get_runner(self, repo_name: str) -> PytestDiffRunner:
        """
        Initialize or retrieve an existing runner for Repo
        """
        runner = self.runners.get(repo_name, "")
        if runner:
            return runner

        repo_conf, status = self.api_client.get(f"/repo/get/{repo_name}")
        repo_conf = RepoConfig(**repo_conf)
        runner = PytestDiffRunner(repo_conf)
        self.runners[repo_name] = runner

        return runner

    def fetch_tasks_thread(self):
        """
        Fetches task from server, single thread
        """
        task_res, status = self.api_client.poll()
        if task_res:
            for t in task_res:
                task = RunTestTaskClient(**t, **t["task_args"])
                self.curr_t.append(task.task_id)
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

        with self.lock:
            self.curr_t.remove(task.task_id)
            self.completed += 1
            print("Outstanding tasks: ", len(self.curr_t))
            print("Total completed: ", self.completed)

    def start_polling(self):
        while True:
            # print("Polling server at: ", self.fetch_endpoint)
            fetch_tasks = threading.Thread(target=self.fetch_tasks_thread, daemon=True)
            fetch_tasks.start()

            time.sleep(1.0)  # Poll every 'interval' second

    # TODO: might be better to write to pipe stdout and redir on the caller side,
    # because multiple processes can potentially be started and mess up the files
    def heart_beat(self):
        new_file_mode = False
        # create file
        if not self.heart_beat_fp.exists():
            with open(self.heart_beat_fp, "w") as f:
                f.write("")

        with open(self.heart_beat_fp, "r") as f:
            raw = f.read()
            if len(raw) > 10**6:
                new_file_mode = True

        with open(self.heart_beat_fp, "w" if new_file_mode else "a") as f:
            curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(curr_time + "\n")

    def start_heartbeat(self):
        while True:
            threading.Thread(target=self.heart_beat, daemon=True).start()

            time.sleep(self.heart_beat_interval)


if __name__ == "__main__":
    import sys

    # dont actually use the db here, its needed as a dep for APIClient (rethink this)
    # but we dont want to mess with local db state from this code
    db = Database()
    api = APIClient(db)

    if len(sys.argv) < 2:
        print("Please provide a heartbeat file path and interval")
        sys.exit(1)

    hb_path = sys.argv[1]
    hb_interval = int(sys.argv[2])

    BGClient(api, TASK_ENDPOINT, hb_path, hb_interval)

    # keep main thread alive so we can terminate all threads via sys interrupt
    while True:
        time.sleep(1.0)
