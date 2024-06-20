from cowboy.config import TASK_ENDPOINT
from cowboy.runner.python import PytestDiffRunner
from cowboy.db.core import Database
from cowboy.repo.models import RepoConfig
from cowboy.http import APIClient
from cowboy.logger import task_log
from cowboy_lib.api.runner.shared import RunTestTaskArgs, Task, TaskResult, TaskType

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime
from pathlib import Path
import threading
import time
import json
from requests import ConnectionError


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

        repo_conf = self.api_client.get(f"/repo/get/{repo_name}")
        repo_conf = RepoConfig(**repo_conf)
        runner = PytestDiffRunner(repo_conf)
        self.runners[repo_name] = runner

        return runner

    def start_polling(self):
        while True:
            try:
                task_res = self.api_client.poll()
                if task_res:
                    task_log.info(f"Receieved {len(task_res)} tasks from server")
                    for t in task_res:
                        if t["type"] == TaskType.RUN_TEST:
                            print("Task: ", t)
                            task = Task(
                                **t,
                                task_args=RunTestTaskArgs.from_json(**t["task_args"]),
                            )
                            self.curr_t.append(task.task_id)
                            threading.Thread(target=self.run_task, args=(task,)).start()

            # These errors result from how we handle server restarts
            # and our janky non-db auth method so can just ignore
            except (TypeError, ConnectionError):
                pass

            time.sleep(1.0)  # Poll every 'interval' second

    def run_task(self, task: Task):
        """
        Runs task and updates its result field when finished
        """
        try:
            task_log.info(f"Starting task: {task.task_id}")
            runner = self.get_runner(task.repo_name)
            cov_res, *_ = runner.run_testsuite(task.task_args)
            task.result = TaskResult(**cov_res.to_dict())
            self.complete_task(task)

        except Exception as e:
            task.result = TaskResult(exception=str(e))
            self.complete_task(task)
            task_log.error(f"Exception from runner: {e} : {type(e).__name__}")

    def complete_task(self, task: Task):
        # Note: json() actually converts nested objects, unlike dict
        self.api_client.post(f"/task/complete", json.loads(task.json()))

        # with self.lock:
        #     self.curr_t.remove(task.task_id)
        #     self.completed += 1
        #     task_log.info(f"Outstanding tasks: {len(self.curr_t)}")
        #     task_log.info(f"Total completed: {self.completed}")

    def heart_beat(self):
        new_file_mode = False
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
    import logging
    from cowboy.logger import file_formatter

    def get_console_handler():
        """
        Returns a console handler for logging.
        """
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(file_formatter)
        return console_handler

    # dont actually use the db here, its needed as a dep for APIClient (rethink this)
    # but we dont want to mess with local db state from this code
    db = Database()
    api = APIClient(db)

    if len(sys.argv) < 3:
        task_log.info(
            "Usage: python client.py <heartbeat_file> <heartbeat_interval> <console>"
        )
        sys.exit(1)

    hb_path = sys.argv[1]
    hb_interval = int(sys.argv[2])
    console = bool(sys.argv[3])

    if console:
        task_log.addHandler(get_console_handler())

    BGClient(api, TASK_ENDPOINT, hb_path, hb_interval)

    # keep main thread alive so we can terminate all threads via sys interrupt
    # (because main thread is the only one we can send signals to)
    while True:
        time.sleep(1.0)
