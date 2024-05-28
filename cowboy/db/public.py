from cowboy.config import COWBOY_FRONTEND_CONFIG, API_ENDPOINT
import json
from pathlib import Path


class FrontEndConfig:
    def __init__(self):
        if not Path(COWBOY_FRONTEND_CONFIG).exists():
            config = {}
            config["api_endpoint"] = API_ENDPOINT
            with open(COWBOY_FRONTEND_CONFIG, "w") as f:
                f.write(json.dumps(config, indent=2))

    def read(self):
        return json.load(open(COWBOY_FRONTEND_CONFIG, "r"))

    def write(self, key, val):
        print("WRITING : ", val)
        self.config = self.read()
        self.config[key] = val
        print(self.config)

        with open(COWBOY_FRONTEND_CONFIG, "w") as f:
            f.write(json.dumps(self.config, indent=2))
