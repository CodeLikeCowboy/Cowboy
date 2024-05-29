from platformdirs import user_data_path
from pathlib import Path

CLIENT_MODE = "debug"

if CLIENT_MODE == "debug":
    COWBOY_DIR = Path(".")
elif CLIENT_MODE == "release":
    COWBOY_DIR = Path(user_data_path())

REPO_ROOT = COWBOY_DIR / "repos"
USER_CONFIG = COWBOY_DIR / ".user"
DB_PATH = (
    COWBOY_DIR / "cowboy/db/db.json"
    if CLIENT_MODE == "debug"
    else COWBOY_DIR / "db.json"
)
HB_PATH = COWBOY_DIR / ".heartbeat"
HB_INTERVAL = 2

NUM_CLONES = 3

LOG_DIR = COWBOY_DIR / "logs"

API_ENDPOINT = "http://18.223.150.134:3000"
TASK_ENDPOINT = f"{API_ENDPOINT}/task/get"

# for frontend
COWBOY_FRONTEND_CONFIG = Path("static/build/config.json")
