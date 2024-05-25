import click
import yaml
from pathlib import Path
import json

from cowboy.repo.models import RepoConfig, RepoConfigRepository, PythonConf
from cowboy.repo.repo import create_cloned_folders, delete_cloned_folders
from cowboy.api_cmds import api_baseline, api_coverage, api_tm_coverage, api_augment
from cowboy.exceptions import CowboyClientError
from cowboy import config
from cowboy.task_client import Manager

from cowboy.db.core import Database
from cowboy.http import APIClient

# yeah global scope, sue me
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


# TODO: should we make initialization a user dialogue instead?
@cowboy_cli.command("init")
def init():
    """Initializes user account for Cowboy."""
    try:
        with open(".user", "r") as f:
            user_conf = yaml.safe_load(f)
    except FileNotFoundError:
        click.secho('User definition file ".user" does not exist', fg="red")
        return

    # only allow one user to be registered at a time
    registered = db.get("registered", False)
    if registered:
        click.secho(
            "We are currently only supporting one user per client. If you want to re-register, "
            "first delete the current user via 'cowboy delete_user'",
            fg="red",
        )
        return

    _, status = api.post("/user/register", user_conf)

    db.save_upsert("registered", True)
    db.save_upsert("user", user_conf["email"])

    if status == 200:
        click.secho(
            "Successfully registered user. You can delete .user in case you dont want "
            "passwords/sensitive tokens to be exposed locally",
            fg="green",
        )


@cowboy_cli.command("reset")
def reset():
    """Resets user account for Cowboy ."""
    for repo in db.get("repos", []):
        delete_cloned_folders(Path(config.REPO_ROOT), repo)

    _, status = api.get(f"/user/delete")

    db.reset()

    click.secho("Successfully reset user data", fg="green")


@cowboy_cli.command("dump")
def dump():
    """Dumps db.json for debugging."""
    print(db.get_all())


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
        repo_config, Path(config.REPO_ROOT), db, config.NUM_CLONES
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
        delete_cloned_folders(Path(config.REPO_ROOT), repo_name)
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

    delete_cloned_folders(Path(config.REPO_ROOT), repo_name)
    click.secho(f"Deleted repo {repo_name}", fg="green")


@cowboy_repo.command("augment")
@click.argument("repo_name")
@click.argument("mode")
@click.argument("file", required=False)
@click.argument("tms", required=False)
def augment(repo_name, mode, file, tms):
    """
    Augments existing test modules with new test cases
    """

    res, status = api_augment(repo_name, mode, file, tms)

    if status == 200:
        results, status = api.get(f"/test-gen/results/{repo_name}")
        for r in results:
            print(json.dumps(r, indent=4))


def entrypoint():
    """The entry that the CLI is executed from"""

    try:
        # TODO: we should make a note that currently only supporting
        # running a single repo-at-a-time usage, due to hb and error file conflicts
        runner = Manager(config.HB_PATH, config.HB_INTERVAL)
        cowboy_cli()
    except CowboyClientError as e:
        click.secho(
            f"CowboyClientError: {e}\n {config.SAD_KIRBY}",
            bold=True,
            fg="red",
        )
    except Exception as e:
        raise e
        error_msg = f"ERROR: {e}"
        if db.get("debug", False):
            import traceback

            tb = traceback.format_exc()
            error_msg = f"ERROR: {e}\n{tb}"

        click.secho(error_msg, bold=True, fg="red")


if __name__ == "__main__":
    entrypoint()
