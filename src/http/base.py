from urllib.parse import urljoin

import requests
import logging
import json

from src.config import API_ENDPOINT
from src.db.core import Database

logger = logging.getLogger(__name__)


class HTTPError(Exception):
    pass


class APIClient:
    def __init__(self, db: Database):
        self.server = API_ENDPOINT
        self.db = db

        # user auth token
        self.token = self.db.get("token", "")

    def get(self, uri: str):
        url = urljoin(self.server, uri)

        res = requests.get(url, headers={"Authorization": f"Bearer {self.token}"})

        return self.parse_response(res)

    def post(self, uri: str, data: dict):
        url = urljoin(self.server, uri)

        res = requests.post(
            url, json=data, headers={"Authorization": f"Bearer {self.token}"}
        )

        return self.parse_response(res)

    def delete(self, uri: str):
        url = urljoin(self.server, uri)

        res = requests.delete(url, headers={"Authorization": f"Bearer {self.token}"})

        return self.parse_response(res)

    def parse_response(self, res: requests.Response):
        """
        Parses token from response and handles HTTP exceptions, including retries and timeouts
        """
        json_res = res.json()

        if isinstance(json_res, dict):
            auth_token = json_res.get("token", None)
            if auth_token:
                self.db.save_upsert("token", auth_token)

        if res.status_code == 401:
            raise HTTPError("Unauthorized, are you registered or logged in?")

        if res.status_code == 422:
            message = res.json()["detail"][0]["msg"]
            raise HTTPError(json.dumps(res.json(), indent=2))

        if res.status_code == 500:
            raise HTTPError("Internal server error")
        return json_res, res.status_code
