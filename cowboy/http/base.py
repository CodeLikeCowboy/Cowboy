from urllib.parse import urljoin

import requests
import logging
import json

from cowboy.config import API_ENDPOINT
from cowboy.db.core import Database

logger = logging.getLogger(__name__)


class HTTPError(Exception):
    pass


class APIClient:
    def __init__(self, db: Database):
        self.server = API_ENDPOINT
        self.db = db

        # user auth token
        self.token = self.db.get("token", "")
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # polling state
        self.encountered_401s = 0

    def poll(self):
        """
        Polls the server for new tasks that comes through. Reason we implement
        this method differently than others is because we require some pretty
        janky logic -> basically an alternative auth token
        """
        url = urljoin(self.server, "/task/get")
        res = requests.get(url, headers=self.headers)

        task_token = res.headers.get("set-x-task-auth", None)
        if task_token:
            self.headers["x-task-auth"] = task_token

        # next two conds are used to detect when the server restarts
        if self.headers.get("x-task-auth", None) and res.status_code == 401:
            self.encountered_401s += 1

        if self.encountered_401s > 3:
            self.headers["x-task-auth"] = None
            self.encountered_401s = 0

        return res.json(), res.status_code

    def get(self, uri: str):
        url = urljoin(self.server, uri)

        res = requests.get(url, headers=self.headers)

        return self.parse_response(res)

    def post(self, uri: str, data: dict):
        url = urljoin(self.server, uri)

        res = requests.post(url, json=data, headers=self.headers)

        return self.parse_response(res)

    def delete(self, uri: str):
        url = urljoin(self.server, uri)

        res = requests.delete(url, headers=self.headers)

        return self.parse_response(res)

    def parse_response(self, res: requests.Response):
        """
        Parses token from response and handles HTTP exceptions, including retries and timeouts
        """
        json_res = res.json()
        if isinstance(json_res, dict):
            auth_token = json_res.get("token", None)
            if auth_token:
                print("Successful login, saving token...")
                self.db.save_upsert("token", auth_token)

        if res.status_code == 401:
            raise HTTPError("Unauthorized, are you registered or logged in?")

        if res.status_code == 422:
            message = res.json()["detail"][0]["msg"]
            raise HTTPError(json.dumps(res.json(), indent=2))

        if res.status_code == 500:
            raise HTTPError("Internal server error")
        return json_res, res.status_code
