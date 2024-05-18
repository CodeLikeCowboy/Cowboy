import click
import yaml
from pathlib import Path
import json

from cowboy.repo.models import RepoConfig, RepoConfigRepository, PythonConf
from cowboy.repo.repo import create_cloned_folders, delete_cloned_folders
from cowboy.api_cmds import api_baseline, api_coverage, api_tm_coverage


from cowboy.exceptions import CowboyClientError
from cowboy.config import SAD_KIRBY, REPO_ROOT, TASK_ENDPOINT, HB_PATH, HB_INTERVAL

from cowboy.db.core import Database
from cowboy.http import APIClient

import subprocess
from datetime import datetime, timedelta

import sys

# note that the BGClient is meant to be longer living than a CLI session
# which is why we are spinning off a separate process


# TODO: probably need to add a shutdown all clients cmd
class BGRunner:
    """
    Interacts with client running in background
    """

    def __init__(self, heart_beat_fp: Path, heart_beat_interval: int = 5):
        self.heart_beat_fp = heart_beat_fp
        self.heart_beat_interval = heart_beat_interval

        if not self.is_alive():
            print("Cient not alive starting client")
            self.start_client()
        else:
            print("Client is alive!")

    def start_client(self):
        subprocess.Popen(
            [
                "python",
                "-m",
                "cowboy.task_client.runtest_client",
                str(self.heart_beat_fp),
                str(self.heart_beat_interval),
            ],
            stdout=None,
            stderr=None,
        )

    def is_alive(self):
        if not self.read_beat():
            return False

        # adding one to the interval to account lag
        if datetime.now() - self.read_beat() < timedelta(
            seconds=self.heart_beat_interval + 1
        ):
            return True

        return False

    def read_beat(self):
        try:
            with open(self.heart_beat_fp, "r") as f:
                hb_time = f.readlines()[-1].strip()

                return datetime.strptime(hb_time, "%Y-%m-%d %H:%M:%S")
        except FileNotFoundError:
            return None


# yeah global scope, sue me
# TODO: no but actually lets change this
db = Database()
api = APIClient(db)
rc_repo = RepoConfigRepository(db)


def owner_name_from_url(url: str):
    owner, repo_name = url.split("/")[-2:]
    return owner, repo_name


@click.group()
def cowboy_cli():
    """Command-line interface to Cowboy."""
    pass


# TODO: make this into a dialogue and store the results in DB.json, inside
# of the repo root folder
@cowboy_cli.command("init")
def init():
    """Initializes user account for Cowboy."""
    try:
        with open(".user", "r") as f:
            user_conf = yaml.safe_load(f)
    except FileNotFoundError:
        click.secho("Config file does not exist.", fg="red")
        return

    # only allow one user to be registered at a time
    registered = db.get("registered", False)
    if registered:
        click.secho(
            "We are currently only supporting one user per client. If you want to re-register, \
            first delete the current user via 'cowboy delete_user'",
            fg="red",
        )
        return

    _, status = api.post("/register", user_conf)

    db.save_upsert("registered", True)
    if status == 200:
        click.secho("Successfully registered user", fg="green")


@cowboy_cli.command("delete_user")
def delete_user():
    click.secho("Not yet implemented", fg="red")


# @cowboy_cli.command("login")
# @click.argument("email")
# @click.argument("password")
# def login(email, password):
#     _, status = api.post("/login", {"email": email, "password": password})
#     if status == 200:
#         click.secho("Successfully logged in", fg="green")


@cowboy_cli.group("repo")
def cowboy_repo():
    """Container for all repo commands."""
    pass


# TODO: handle naming conflicts ...
@cowboy_repo.command("create")
@click.argument("config_path")
def repo_init(config_path):
    """Initializes a new repo."""
    try:
        with open(config_path, "r") as f:
            repo_config = yaml.safe_load(f)
    except FileNotFoundError:
        click.secho("Config file does not exist.", fg="red")
        return

    repo_name = repo_config["repo_name"]
    click.echo("Initializing new repo {}".format(repo_name))

    python_conf = PythonConf(
        cov_folders=repo_config.get("cov_folders", []),
        test_folder=repo_config.get("test_folder", ""),
        interp=repo_config.get("interp"),
        pythonpath=repo_config.get("pythonpath", ""),
    )

    repo_config = RepoConfig(
        repo_name=repo_name,
        url=repo_config.get("url"),
        cloned_folders=[],
        source_folder="",
        python_conf=python_conf,
    )

    cloned_folders = create_cloned_folders(
        repo_config, Path(REPO_ROOT), db.get("num_repos")
    )
    repo_config.cloned_folders = cloned_folders

    try:
        api.post("/repo/create", repo_config.serialize())
        print(json.dumps(repo_config.serialize(), indent=4))
        click.secho("Successfully created repo: {}".format(repo_name), fg="green")

        # starting baseline
        # click.secho("Starting baseline", fg="green")

        # api_coverage(repo_name)
        api_baseline(repo_name)

    # should we differentiate between timeout/requests.exceptions.ConnectionError?
    except Exception as e:
        click.secho(f"Repo creation failed on server: {e}", fg="red")
        click.secho(f"Rolling back repo creation", fg="red")
        delete_cloned_folders(Path(REPO_ROOT), repo_name)
        return


@cowboy_repo.command("clean")
@click.argument("repo_name")
def clean(repo_name):
    """
    Deletes all branches that still exists (assumption is that all good
    branches are merged and deleted)
    """
    _, status = api.delete(f"/repo/clean/{repo_name}")
    if status != 200:
        click.secho(f"Failed to clean repo {repo_name}", fg="red")
        return

    click.secho(f"Cleaned repo {repo_name}", fg="green")


# TODO: remove these commands?
@cowboy_repo.command("coverage")
@click.argument("repo_name")
def cmd_coverage(repo_name):
    api_coverage(repo_name)


@cowboy_repo.command("baseline")
@click.argument("repo_name")
def cmd_baseline(repo_name):
    api_baseline(repo_name)


@cowboy_repo.command("sorted_coverage")
@click.argument("repo_name")
def cmd_sorted_coverage(repo_name):
    api_tm_coverage(repo_name)


@cowboy_repo.command("delete")
@click.argument("repo_name")
def delete(repo_name):
    """
    Deletes all repos and reset the database
    """
    _, status = api.delete(f"/repo/delete/{repo_name}")
    if status != 200:
        click.secho(f"Failed to delete repo {repo_name}", fg="red")
        return

    delete_cloned_folders(Path(REPO_ROOT), repo_name)

    click.secho(f"Deleted repo {repo_name}", fg="green")


@cowboy_repo.command("augment")
@click.argument("repo_name")
# @click.argument("files", required=False, nargs=-1)
# @click.option("--all", is_flag=True)
@click.option("--auto", is_flag=True)
def augment(repo_name, auto):
    """
    Augments existing test modules with new test cases
    """
    mode = None
    tm_names = []

    if auto:
        mode = "auto"
        tm_names = []

    merge_urls = api.post(
        "/test-gen/augment",
        {"tm_names": tm_names, "repo_name": repo_name, "mode": "auto"},
    )


def entrypoint():
    """The entry that the CLI is executed from"""

    try:
        # runner = BGRunner(HB_PATH, HB_INTERVAL)
        cowboy_cli()
    except CowboyClientError as e:
        click.secho(
            f"UNHANDLED RUNTIME ERROR: {e}\nPlease file a bug report, {SAD_KIRBY}",
            bold=True,
            fg="red",
        )
    except Exception as e:
        error_msg = f"ERROR: {e}"
        if db.get("debug", False):
            import traceback

            tb = traceback.format_exc()
            error_msg = f"ERROR: {e}\n{tb}"

        click.secho(error_msg, bold=True, fg="red")


if __name__ == "__main__":
    entrypoint()
