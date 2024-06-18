import random
import string
import threading
from queue import Queue


def gen_random_name():
    """
    Generates a random name using ASCII, 8 characters in length
    """

    return "".join(random.choices(string.ascii_lowercase, k=8))


def start_daemon(task, args):
    """
    Starts a daemon thread that continuously joins/checks is_alive to
    allow for sigints to pass thru (which would otherwise get consumed
    by some blocking python functions)
    """
    result_queue = Queue()

    def target():
        try:
            result = task(*args)
            result_queue.put((None, result))
        except Exception as e:
            result_queue.put((e, None))

    t = threading.Thread(target=target, daemon=True)
    t.start()

    try:
        while t.is_alive():
            t.join(timeout=0.1)  # Allow signal handling
    except KeyboardInterrupt:
        raise KeyboardInterrupt

    exception, result = result_queue.get()
    if exception:
        raise exception

    return result


def is_port_available(port):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False
