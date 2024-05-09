import click
import yaml
from pathlib import Path
import sys

from src.repo.models import RepoConfig, RepoConfigRepository, PythonConf
from src.repo.repo import create_cloned_folders, delete_cloned_folders
from src.db.core import Database
from src.http.base import APIClient

from src.api_cmds import api_baseline, api_coverage


from src.exceptions import CowboyClientError

from src.config import SAD_KIRBY, REPO_ROOT

db = Database()
api = APIClient(db)
rc_repo = RepoConfigRepository(db)

# client = RunTestClient(api, TASK_ENDPOINT)


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

    _, status = api.post("/register", user_conf)
    if status == 200:
        click.secho("Successfully registered user", fg="green")


@cowboy_cli.command("login")
@click.argument("email")
@click.argument("password")
def login(email, password):
    _, status = api.post("/login", {"email": email, "password": password})
    if status == 200:
        click.secho("Successfully logged in", fg="green")


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
        import json

        api.post("/repo/create", repo_config.serialize())       
        print(json.dumps(repo_config.serialize(), indent=4))
        click.secho("Successfully created repo: {}".format(repo_name), fg="green")

        # starting baseline
        click.secho("Starting baseline", fg="green")

        api_coverage(repo_name)
        api_baseline(repo_name)

    # should we differentiate between timeout/requests.exceptions.ConnectionError?
    except Exception as e:
        click.secho(f"Repo creation failed on server: {e}", fg="red")
        click.secho(f"Rolling back repo creation", fg="red")
        delete_cloned_folders(Path(REPO_ROOT), repo_name)
        return


# TODO: remove these commands?
@cowboy_repo.command("coverage")
@click.argument("repo_name")
def cmd_coverage(repo_name):
    api_coverage(repo_name)


@cowboy_repo.command("baseline")
@click.argument("repo_name")
def cmd_baseline(repo_name):
    api_baseline(repo_name)


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


def entrypoint():
    """The entry that the CLI is executed from"""

    try:
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
