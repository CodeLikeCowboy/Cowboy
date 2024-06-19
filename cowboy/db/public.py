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

    config = Path("build/config.json")
    with config.open("w") as config:
        config.write(json.dumps(env_vars))
