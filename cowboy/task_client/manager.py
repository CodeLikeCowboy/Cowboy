from cowboy_lib.utils import locate_python_interpreter

from pathlib import Path
import subprocess
from datetime import datetime, timedelta
import subprocess


class Manager:
    """
    Interacts with client running in background
    """

    def __init__(
        self, heart_beat_fp: Path, heart_beat_interval: int = 5, console: bool = False
    ):
        self.heart_beat_fp = heart_beat_fp
        self.heart_beat_interval = heart_beat_interval
        self.console = console
        self.interp = locate_python_interpreter()

        if not self.is_alive():
            # print("Client not alive starting client")
            self.start_client()
        # else:
        # print("Client is alive!")

    def start_client(self):
        subprocess.Popen(
            [
                self.interp,
                "-m",
                "cowboy.task_client.client",
                str(self.heart_beat_fp),
                str(self.heart_beat_interval),
                "True",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def is_alive(self):
        """
        Checks that client is still alive if last beat is within
        time interval
        """
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

        except ValueError as e:
            print(
                f"Possibly corrupted file: {str(self.heart_beat_fp.resolve())}, try deleting "
            )
        except FileNotFoundError:
            return None
