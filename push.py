from cowboy_lib.repo import GitRepo
from pathlib import Path

repo = GitRepo(Path("repos/test_codecov"))
merge_url = repo.checkout_and_push("test_name1", "hello1", ["world.txt"])

print(merge_url)
