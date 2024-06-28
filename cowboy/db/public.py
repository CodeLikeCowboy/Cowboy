from cowboy.config import REACT_CONFIG_PATH
from pathlib import Path
import json


def init_react_env_vars(token, api_endpoint):
    """
    Init the .env file in the react folder
    """
    env_vars = {
        "jwt_token": token,
        "api_endpoint": api_endpoint,
    }

    with open(REACT_CONFIG_PATH, "w+") as f:
        f.write(json.dumps(env_vars))
