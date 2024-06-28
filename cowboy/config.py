import importlib.resources as pkg_resources
from platformdirs import user_data_path
from pathlib import Path


CLIENT_MODE = "release"

if CLIENT_MODE == "debug":
    # assume that we are executing from the root of the cowboy directory in debug mode
    COWBOY_DIR = Path(".")
elif CLIENT_MODE == "release":
    COWBOY_DIR = Path(user_data_path())

# Paths
REPO_ROOT = COWBOY_DIR / "repos"
USER_CONFIG = COWBOY_DIR / ".user"
DB_PATH = COWBOY_DIR / "db.json"
LOG_DIR = COWBOY_DIR / "logs"
COWBOY_FRONTEND_CONFIG = COWBOY_DIR / "build/config.json"

# React front-end
REACT_DIST_DIR = (
    Path(str(pkg_resources.files("cowboy"))) / "build"
    if CLIENT_MODE == "release"
    else "build"
)
REACT_DIST_CONFIG = REACT_DIST_DIR / "config.json"

# Client variables
HB_PATH = COWBOY_DIR / ".heartbeat"
HB_INTERVAL = 2
NUM_CLONES = 3
RUN_TEST_TIMEOUT = 300

API_ENDPOINT = "http://18.223.150.134:3000"
TASK_ENDPOINT = f"{API_ENDPOINT}/task/get"
