from cowboy.config import COWBOY_FRONTEND_CONFIG, API_ENDPOINT
from pathlib import Path


def init_react_env_vars(token, api_endpoint):
    """
    Init the .env file in the react folder
    """
    env_vars = {
        "REACT_APP_COWBOY_TOKEN": token,
        "REACT_APP_COWBOY_API_ENDPOINT": api_endpoint,
    }

    env_file_path = Path("static/.env")
    with env_file_path.open("w") as env_file:
        for key, value in env_vars.items():
            env_file.write(f"{key}={value}\n")
