from cowboy.config import TASK_ENDPOINT
from cowboy.runner import PytestDiffRunner, RunnerError
from cowboy.db.core import Database
from cowboy.repo.models import RepoConfig
from cowboy.http import APIClient
from cowboy_lib.api.runner.shared import RunTestTaskArgs, Task, TaskResult, TaskType

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import threading
import _thread
import time
import json
from requests import ConnectionError
import traceback

from logging import getLogger

log = getLogger(__name__)


class BGClient:
    """
    Single Task client that runs as a subprocess in the background
    and fetches tasks from server
    """

    def __init__(
        self,
        api: APIClient,
        fetch_endpoint: str,
        heart_beat_fp: Path,
        heart_beat_interval: int = 5,
        sleep_interval=5,
    ):
        self.api = api
        self.db = db
        self.run_executor = ThreadPoolExecutor(max_workers=5)
        self.fetch_endpoint = fetch_endpoint

        # curr tasks : technically dont need since we await every new
        # tasks via runner.acquire_one() but use for debugging
        self.curr_t = []
        self.completed = 0

        self.runners = {}

        # retrieved tasks
        self.lock = threading.Lock()
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
        Initialize or retrieve ean existing runner for Repo
        """
        # technically we can store all info locally but dont feel like
        # managing repo state de-sync
        repo_conf = self.api.get(f"/repo/get/{repo_name}")

        # need to lock access to self.runners since two threads that
        # instantiate the same runner will not clobber the test repository
        # when they try to execute tests in the same folder without
        # LockedRepos in PytestDiffRunner
        with self.lock:
            if self.runners.get(repo_name, None):
                return self.runners[repo_name]

            repo_conf = RepoConfig(**repo_conf)
            runner = PytestDiffRunner(repo_conf)
            self.runners[repo_name] = runner

        return runner

    def start_polling(self):
        """
        Polls server and receive tasks. Currently only two types:'cowboy.repo.runner'
        1. Run Test -> runs in separate thread
        2. Shutdown -> shutdown client immediately
        """
        while True:
            try:
                task_res = self.api.poll()
                if task_res:
                    log.info(f"Receieved {len(task_res)} tasks from server")
                    for t in task_res:
                        task_type = t["type"]
                        log.info(f"Received task: {t}")
                        if task_type == TaskType.RUN_TEST:
                            task = Task(**t)
                            task.task_args = RunTestTaskArgs.from_json(**t["task_args"])
                            self.curr_t.append(task.task_id)

                            threading.Thread(
                                target=self.run_test_thread, args=(task,)
                            ).start()

                        elif task_type == TaskType.SHUTDOWN:
                            log.info(f"Received shutdown signal")
                            self.complete_task(Task(**t))
                            # sends sigint to main thread
                            _thread.interrupt_main()

            except ConnectionError as e:
                # log.error("Error connecting to server ...")
                pass

            # These errors result from how we handle server restarts
            # and our janky non-db auth method so can just ignore
            except Exception as e:
                log.error(
                    f"Exception from client: {e} : {type(e).__name__}\n{traceback.format_exc()}"
                )

            time.sleep(1.0)  # Poll every 'interval' second

    def run_test_thread(self, task: Task):
        """
        Runs task and updates its result field when finished
        """
        try:
            log.info(f"Starting task: {task.task_id}")

            runner = self.get_runner(task.task_args.repo_name)

            log.info(f"Running testsuite for {task.task_args.repo_name} ...")
            cov_res, *_ = runner.run_testsuite(task.task_args)
            task.result = TaskResult(**cov_res.to_dict())
            self.complete_task(task)

        except RunnerError as e:
            task.result = TaskResult(exception=str(e))
            self.complete_task(task)

            log.error(f"Exception from runner: {e}\n{traceback.format_exc()}")

    def complete_task(self, task: Task):
        self.api.post(f"/task/complete", json.loads(task.json()))

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
    from cowboy.logger import formatter

    def get_console_handler():
        """
        Returns a console handler for logging.
        """
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        return console_handler

    if len(sys.argv) < 3:
        log.info(
            "Usage: python client.py <heartbeat_file> <heartbeat_interval> <console>"
        )
        sys.exit(1)

    hb_path = sys.argv[1]
    hb_interval = int(sys.argv[2])
    console = bool(sys.argv[3])

    if console:
        log.addHandler(get_console_handler())

    db = Database()
    api = APIClient(db)
    BGClient(api, TASK_ENDPOINT, hb_path, hb_interval)
    # keep main thread alive so we can terminate all threads via sys interrupt
    # (because main thread is the only one we can send signals to)
    while True:
        time.sleep(1.0)
