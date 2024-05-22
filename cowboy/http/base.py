from cowboy.config import API_ENDPOINT
from cowboy.db.core import Database

from urllib.parse import urljoin
from threading import Thread
import requests
import logging
import json
from queue import Queue
import signal
import sys

logger = logging.getLogger(__name__)


def parse_pydantic_error(error_json):
    """
    Parse the Pydantic error JSON object and format it into a readable string message.

    :param error_json: JSON object returned by Pydantic containing error details.
    :return: Formatted string message.
    """
    error_obj = json.loads(error_json)
    details = error_obj.get("detail", [])

    messages = []
    for detail in details:
        loc = detail.get("loc", [])
        msg = detail.get("msg", "")
        error_type = detail.get("type", "")

        location = " -> ".join(map(str, loc))
        messages.append(f"Location: {location}\nMessage: {msg}\nType: {error_type}\n")

    return "\n".join(messages)


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

    def long_post(self, uri: str, data: dict):
        """
        Need this method to handle long requests, because requests consume
        all sigints while waiting for the response to return, we have to wrap
        it in a new thread and use is_alive/join(timeout) to allow the sigint
        to reach the main thread
        """

        url = urljoin(self.server, uri)
        result_queue = Queue()

        def target():
            try:
                result = self.post(url, data)
                result_queue.put(result)
            except Exception as e:
                result_queue.put(e)

        t = Thread(target=target, daemon=True)
        t.start()

        try:
            while t.is_alive():
                t.join(timeout=0.1)  # Allow signal handling
        except KeyboardInterrupt:
            sys.exit()

        result = result_queue.get()
        return result

    def get(self, uri: str):
        url = urljoin(self.server, uri)

        res = requests.get(url, headers=self.headers)

        return self.parse_response(res)

    def post(self, uri: str, data: dict, thread=False):
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
