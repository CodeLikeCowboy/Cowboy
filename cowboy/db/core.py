import json
import os
from typing import Dict

from cowboy.exceptions import CowboyClientError
from cowboy.config import DB_PATH


class KeyNotFoundError(CowboyClientError):
    def __init__(self, key):
        super().__init__(f"Key {key} not found in DB")


class Database:
    """
    KV DB impl
    """

    _instance = None

    def __new__(cls, db_path: str = DB_PATH):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = DB_PATH):
        """
        Initialize empty json at db_path
        """
        self.db_path = db_path

        if not os.path.exists(db_path):
            if os.path.isdir(db_path):
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            with open(db_path, "w") as f:
                f.write("{}")

        # in case emtpy file or db gets corrupted
        elif os.path.exists(db_path):
            try:
                with open(db_path, "r") as f:
                    json.load(f)
            except json.JSONDecodeError:
                print("DB corrupted, re-initializing ...")
                with open(db_path, "w") as f:
                    f.write("{}")

    def save_upsert(self, key, value):
        """
        Overwrites key if it exists, otherwise creates it
        """
        try:
            data = self.get_all()
            data[key] = value
            with open(self.db_path, "w") as f:
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
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=2)

        except IOError as e:
            print(f"Error saving to DB file: {e}")

    def save_to_list(self, key, value):
        """
        Adds a value to a list
        """
        try:
            data = self.get_all()
            if not data.get(key, None):
                data[key] = []

            data[key].append(value)
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=2)

        except IOError as e:
            print(f"Error saving to DB file: {e}")

    def delete_from_list(self, key, value):
        """
        Deletes a value from a list
        """
        try:
            data = self.get_all()
            data[key].remove(value)
        except KeyError:
            return

        with open(self.db_path, "w") as f:
            json.dump(data, f)

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
        with open(self.db_path, "w") as f:
            json.dump(data, f)

    def delete(self, key):
        data = self.get_all()
        if key in data:
            del data[key]
            with open(self.db_path, "w") as f:
                json.dump(data, f)
        else:
            raise KeyNotFoundError(key)

    def reset(self):
        with open(self.db_path, "w") as f:
            f.write("{}")

    def get_all(self) -> Dict:
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, "r") as f:
                    return json.load(f)
            else:
                return {}
        except IOError as e:
            print(f"Error reading from DB file: {e}")
            return {}
