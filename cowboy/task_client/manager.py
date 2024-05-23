from cowboy.utils import locate_python_interpreter
from cowboy.logger import task_log

from pathlib import Path
import subprocess
from datetime import datetime, timedelta
import subprocess
import select
import threading


class Manager:
    """
    Interacts with client running in background
    """

    def __init__(self, heart_beat_fp: Path, heart_beat_interval: int = 5):
        self.heart_beat_fp = heart_beat_fp
        self.heart_beat_interval = heart_beat_interval
        self.interp = locate_python_interpreter()

        if not self.is_alive():
            print("Client not alive starting client")
            self.start_client()
        else:
            print("Client is alive!")

    def start_client(self):
        subprocess.Popen(
            [
                self.interp,
                "-m",
                "cowboy.task_client.client",
                str(self.heart_beat_fp),
                str(self.heart_beat_interval),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def read_fd(self, fd):
        r_list, w_list, ex_list = select.select([fd], [], [], 0.1)
        if r_list:
            lines = fd.readlines()
            if not lines:
                return []
            return [l.strip() for l in lines]

        return []

    def is_alive(self):
        if not self.read_beat():
            return False

        # adding one to the interval to account lag
        if datetime.now() - self.read_beat() < timedelta(
            seconds=self.heart_beat_interval + 1
        ):
            return True

        return False

    def read_beat(self):
        try:
            with open(self.heart_beat_fp, "r") as f:
                hb_time = f.readlines()[-1].strip()

                return datetime.strptime(hb_time, "%Y-%m-%d %H:%M:%S")
        except FileNotFoundError:
            return None
