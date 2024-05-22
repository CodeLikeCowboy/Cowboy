import logging
import os
from datetime import datetime

from typing import Literal, Mapping

from cowboy.config import LOG_DIR


file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s",
    datefmt="%H:%M:%S",
)


def get_file_handler(log_dir=LOG_DIR):
    """
    Returns a file handler for logging.
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    file_name = f"runner_{timestamp}.log"
    file_handler = logging.FileHandler(os.path.join(log_dir, file_name))
    # if config.debug:
    #     file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    return file_handler


runnerlogger = logging.getLogger("runnerlogger")
runnerlogger.setLevel(logging.INFO)
runnerlogger.addHandler(get_file_handler())
