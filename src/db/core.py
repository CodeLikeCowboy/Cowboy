import json
import os
from typing import Dict
from pathlib import Path


class Database:
    """
    KV DB impl
    """

    def __init__(self, filepath: str = "src/db/db.json"):
        self.filepath = filepath

    def save_upsert(self, key, value):
        try:
            data = self.get_all()
            data[key] = value
            with open(self.filepath, "w") as f:
                json.dump(data, f)
        except IOError as e:
            print(f"Error saving to DB file: {e}")

    def get(self, key):
        return self.get_all().get(key, None)

    def delete(self, key):
        data = self.get_all()
        if key in data:
            del data[key]
            with open(self.filepath, "w") as f:
                json.dump(data, f)

    def get_all(self) -> Dict:
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r") as f:
                    return json.load(f)
            else:
                return {}
        except IOError as e:
            print(f"Error reading from DB file: {e}")
            return {}
