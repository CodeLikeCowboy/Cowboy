import json
import os
from typing import Dict

from cowboy.exceptions import CowboyClientError


class KeyNotFoundError(CowboyClientError):
    def __init__(self, key):
        super().__init__(f"Key {key} not found in DB")


class Database:
    """
    KV DB impl
    """

    _instance = None

    def __new__(cls, filepath: str = "src/db/db.json"):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.filepath = filepath
        return cls._instance

    def __init__(self, filepath: str = "src/db/db.json"):
        pass

    def save_upsert(self, key, value):
        """
        Overwrites key if it exists, otherwise creates it
        """
        try:
            data = self.get_all()
            data[key] = value
            with open(self.filepath, "w") as f:
                json.dump(data, f)
        except IOError as e:
            print(f"Error saving to DB file: {e}")

    def save_dict(self, dict_key, key, value):
        """
        Adds a key/val pair to existing key
        """
        try:
            data = self.get_all()
            if not data.get(dict_key, None):
                data[dict_key] = {}

            data[dict_key][key] = value
            with open(self.filepath, "w") as f:
                json.dump(data, f, indent=2)

        except IOError as e:
            print(f"Error saving to DB file: {e}")

    def get(self, key, default=None):
        return self.get_all().get(key, default)

    def get_dict(self, dict_key, key):
        data = self.get_all()
        if dict_key in data:
            return data[dict_key].get(key, None)
        return None

    def delete_dict(self, dict_key, key):
        data = self.get_all()
        del data[dict_key][key]
        with open(self.filepath, "w") as f:
            json.dump(data, f)

    def delete(self, key):
        data = self.get_all()
        if key in data:
            del data[key]
            with open(self.filepath, "w") as f:
                json.dump(data, f)
        else:
            raise KeyNotFoundError(key)

    def reset(self):
        with open(self.filepath, "w") as f:
            f.write("{}")

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
