from cowboy.http import APIClient
from cowboy.db.core import Database

db = Database()
api = APIClient(db)


def api_register(user_conf):
    res = api.post(f"/user/register", user_conf)
    return res["token"]
