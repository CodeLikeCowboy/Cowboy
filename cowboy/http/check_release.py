import requests
from cowboy.db.core import Database

PLEASE_UPDATE = """
A new release, {tag}, of Cowboy is available with the follow new features/updates/fixes:
{descr}

Please upgrade to the new version by running:
pip install --upgrade cowboy-client
"""


def check_release(db: Database) -> str:
    old_release = db.get("release", "v0.0.0")
    new_release, descr = get_latest_github_release()

    print(f"Old release: {old_release}, New release: {new_release}")

    db.save_upsert("release", new_release)

    if tag_to_int(new_release) > tag_to_int(old_release):
        return PLEASE_UPDATE.format(tag=new_release, descr=descr)

    return ""


def get_latest_github_release():
    """
    Get the latest release tag and description of a GitHub repository.

    :param owner: Owner of the repository (username or organization)
    :param repo: Name of the repository
    :return: Tuple containing the latest release tag as an integer and the release description as a string,
             or (None, None) if the repository or release is not found
    """
    url = f"https://api.github.com/repos/JohnPeng47/cowboy/releases/latest"
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data["tag_name"], data.get("body", "")
    else:
        print(f"Failed to fetch the latest release.")
        return None, None


def tag_to_int(tag):
    # gets rid of initial 'v' in tag
    version_nums = tag[1:].split(".")
    version_nums.reverse()

    return sum([int(t) * 10**i for i, t in enumerate(version_nums)])


if __name__ == "__main__":
    print(get_latest_github_release())
