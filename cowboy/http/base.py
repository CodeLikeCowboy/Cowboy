from cowboy.config import API_ENDPOINT
from cowboy.db.core import Database
from cowboy.exceptions import CowboyClientError
from cowboy.utils import start_daemon

from urllib.parse import urljoin
import requests
import logging
import json

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


class InternalServerError(Exception):
    pass


class APIClient:
    def __init__(self, db: Database):
        self.server = API_ENDPOINT
        self.db = db

        # secondary auth token for our janky poll auth
        self.pauth_token = None

        # polling state
        self.encountered_401s = 0

    def headers(self):
        token = self.db.get("token", "")
        headers = {"Authorization": f"Bearer {token}"}

        return headers

    def get(self, uri: str):
        url = urljoin(self.server, uri)

        res = requests.get(url, headers=self.headers())

        return self.parse_response(res)

    def post(self, uri: str, data: dict):
        url = urljoin(self.server, uri)
        res = requests.post(url, json=data, headers=self.headers())

        return self.parse_response(res)

    def poll(self):
        """
        Polls the server for new tasks that comes through. Reason we implement
        this method differently than others is because we require some pretty
        janky logic -> basically an alternative auth token
        """
        headers = self.headers()
        if self.pauth_token:
            headers.update({"x-task-auth": self.pauth_token})

        url = urljoin(self.server, "/task/get")
        res = requests.get(url, headers=headers)

        task_token = res.headers.get("set-x-task-auth", None)
        if task_token:
            self.pauth_token = task_token

        # next two conds are used to detect when the server restarts
        if self.pauth_token and res.status_code == 401:
            self.encountered_401s += 1

        if self.encountered_401s > 3:
            self.pauth_token = None
            self.encountered_401s = 0

        return res.json()

    def long_post(self, uri: str, data: dict):
        """
        Need this method to handle long requests, because requests consume
        all sigints while waiting for the response to return, we have to wrap
        it in a new thread and use is_alive/join(timeout) to allow the sigint
        to reach the main thread
        """
        return start_daemon(self.post, (uri, data))

    def long_get(self, uri: str):
        """
        Need this method to handle long requests, because requests consume
        all sigints while waiting for the response to return, we have to wrap
        it in a new thread and use is_alive/join(timeout) to allow the sigint
        to reach the main thread
        """
        return start_daemon(self.get, (uri,))

    def delete(self, uri: str):
        url = urljoin(self.server, uri)

        res = requests.delete(url, headers=self.headers())

        return self.parse_response(res)

    def parse_response(self, res: requests.Response):
        """
        Parses token from response and handles HTTP exceptions, including retries and timeouts
        """
        if res.status_code == 401:
            raise HTTPError("Unauthorized, are you registered or logged in?")

        elif res.status_code == 500:
            raise InternalServerError()

        elif res.status_code == 400 or res.status_code == 422:
            message = res.json()["detail"]

            if isinstance(message, (dict, list)):
                message = json.dumps(message, indent=2)

            raise CowboyClientError(message)

        return res.json()
