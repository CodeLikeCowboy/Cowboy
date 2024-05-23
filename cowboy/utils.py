import random
import string
import shutil
import os
import subprocess


def gen_random_name():
    """
    Generates a random name using ASCII, 8 characters in length
    """

    return "".join(random.choices(string.ascii_lowercase, k=8))


def locate_python_interpreter():
    possible_interpreters = ["python", "python3"]

    for interpreter in possible_interpreters:
        # Check if the interpreter is in PATH
        path = shutil.which(interpreter)
        if path:
            return path

    # Try manually common locations
    common_locations = [
        "/usr/bin/python",
        "/usr/local/bin/python",
        "/usr/bin/python3",
        "/usr/local/bin/python3",
        "/bin/python",
        "/bin/python3",
        "/usr/sbin/python",
        "/usr/sbin/python3",
    ]

    for location in common_locations:
        if os.path.isfile(location) and os.access(location, os.X_OK):
            return location

    # As a last resort, try running "python --version" and "python3 --version"
    for interpreter in possible_interpreters:
        try:
            result = subprocess.run(
                [interpreter, "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return interpreter
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    raise FileNotFoundError("Python interpreter not found on this host")
