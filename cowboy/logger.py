from cowboy.config import LOG_DIR

import logging
import os
from datetime import datetime
import pytz


def converter(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=pytz.utc)
    return dt.astimezone(pytz.timezone("US/Eastern")).timetuple()


def get_file_handler(log_dir=LOG_DIR):
    """
    Returns a file handler for logging.
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    file_name = f"runner_{timestamp}.log"
    file_handler = logging.FileHandler(os.path.join(log_dir, file_name))

    return file_handler


formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s",
    datefmt="%H:%M:%S",
)
formatter.converter = converter

# converter can only be set on the formatter
file_handler = get_file_handler()
file_handler.setFormatter(formatter)


logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler],
)
