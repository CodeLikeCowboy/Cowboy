from cowboy_lib.repo import GitRepo

from cowboy.repo.models import RepoConfig, RepoConfigRepository, PythonConf
from cowboy.repo.repo import (
    create_cloned_folders,
    delete_cloned_folders,
    get_cloned_folders,
)
from cowboy.api_cmds import (
    api_baseline,
    api_augment,
    api_register,
    api_get_tms,
    api_get_head,
)
from cowboy.task_client import Manager
from cowboy.browser import serve_ui
from cowboy.exceptions import CowboyClientError
from cowboy import config

from cowboy.db.core import Database
from cowboy.db.public import init_react_env_vars
from cowboy.http import APIClient, InternalServerError

import click
import yaml
from pathlib import Path
import json

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


@cowboy_cli.command("dump")
def dump():
    """Dumps db.json for debugging."""
    print(db.get_all())


@cowboy_cli.group("user")
def cowboy_user():
    """Container for all user commands."""
    pass


# TODO: make initialization user dialogue instead
@cowboy_user.command("init")
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
            f"or something has gone wrong, manually delete {config.DB_PATH} and run cowboy user init again.",
            fg="red",
        )
        return

    token = api_register(user_conf)

    # save token in python db
    db.save_upsert("token", token)
    db.save_upsert("registered", True)
    db.save_upsert("user", user_conf["email"])

    # initialize the front-end config after
    init_react_env_vars(token, config.API_ENDPOINT)

    click.secho(
        "Successfully registered user. You can delete .user in case you dont want "
        "passwords/sensitive tokens to be exposed locally",
        fg="green",
    )


@cowboy_user.command("update-oai-key")
@click.argument("openai_api_key")
def update_oai(openai_api_key):
    """Updates the openapi key for the user."""

    api.post("/user/update/openai-key", {"openai_api_key": openai_api_key})
    click.secho("Successfully updated openapi key", fg="green")


@cowboy_user.command("reset")
def reset():
    """Resets user account for Cowboy ."""
    api.long_get(f"/user/delete")

    for repo in db.get("repos", []):
        delete_cloned_folders(Path(config.REPO_ROOT), repo)

    db.reset()
    click.secho("Successfully reset user data", fg="green")


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
        is_experiment=repo_config.get("is_experiment", False),
    )

    db.save_to_list("repos", repo_name)
    cloned_folders = create_cloned_folders(
        repo_config, Path(config.REPO_ROOT), db, config.NUM_CLONES
    )
    repo_config.cloned_folders = cloned_folders

    try:
        api.post("/repo/create", repo_config.serialize())
        print(json.dumps(repo_config.serialize(), indent=4))
        click.secho("Successfully created repo: {}".format(repo_name), fg="green")

    except Exception as e:
        error_message = str(e)
        click.secho(f"Repo creation failed on server: {error_message}", fg="red")
        click.secho(f"Rolling back repo creation", fg="red")

        db.delete_from_list("repos", repo_name)

        # leave cloned folders alone for debugging TestSuiteError
        if "RunnerError" in error_message:
            return

        delete_cloned_folders(Path(config.REPO_ROOT), repo_name)
        return


@cowboy_repo.command("delete")
@click.argument("repo_name")
def delete(repo_name):
    """
    Deletes all repos and reset the database
    """
    try:
        api.delete(f"/repo/delete/{repo_name}")
    except Exception:
        click.secho(f"Failed to delete repo {repo_name}", fg="red")
        return

    db.delete_from_list("repos", repo_name)
    delete_cloned_folders(Path(config.REPO_ROOT), repo_name)
    click.secho(f"Deleted repo {repo_name}", fg="green")


NO_SUPPORT_REPO_UPDATES = """
A thousand apologies, dear and valued user, our current backend does not track the HEAD of your remote 
repo; we are currently working on this feature. Will still proceed with the command 
"""

SIT_TIGHT = """
Sit tight this might take a while (>5min) 
"""


@cowboy_repo.command("augment")
@click.argument("repo_name")
@click.option("--mode", required=False)
# NOTE: currently not supported for now
# @click.option("--files", required=False, multiple=True)
@click.option("--tm", required=False, multiple=True)
def augment(repo_name, mode, tm):
    """
    Augments existing test modules with new test cases
    """
    # for grammars sake..
    tms = tm

    if tms:
        mode = "module"
    elif mode == "auto" and tms:
        raise Exception("Cannot specify file or tms when mode=auto")

    repo_folder = get_cloned_folders(repo_name)[0]
    remote_head = api_get_head(repo_name)
    local_head = GitRepo(repo_folder).local_commit
    if remote_head != local_head:
        click.secho(
            f"Local repo HEAD {local_head[:7]} is not up-to-date with remote {remote_head[:7]}\n"
            + NO_SUPPORT_REPO_UPDATES,
            fg="yellow",
        )

    click.secho(SIT_TIGHT, fg="yellow")
    # NOTE: might need to expose baseline command manually to user
    api_baseline(repo_name, mode, tms)
    session_id = api_augment(repo_name, mode, tms)
    serve_ui(session_id)


@cowboy_repo.command("baseline")
@click.argument("repo_name")
@click.option("--mode", required=False)
# NOTE: currently not supported for now
# @click.option("--files", required=False, multiple=True)
@click.option("--tm", required=False, multiple=True)
def augment(repo_name, mode, tm):
    """
    Augments existing test modules with new test cases
    """
    # for grammars sake..
    tms = tm

    if tms:
        mode = "module"
    elif mode == "auto" and tms:
        raise Exception("Cannot specify file or tms when mode=auto")

    # NOTE: might need to expose baseline command manually to user
    api_baseline(repo_name, mode, tms)


@cowboy_repo.command("get_tms")
@click.argument("repo_name")
def get_tms(repo_name):
    """
    Gets all test_modules for a given repo
    """
    tms = api_get_tms(repo_name)
    for tm in tms:
        print("TestModule: ", tm["name"])
        print("TestFile: ", tm["filepath"])
        for i, unit_test in enumerate(tm["unit_tests"], start=1):
            print(f"{i}. {unit_test}")

        print("\n")


@cowboy_cli.command("browser")
@click.argument("session_id")
def browser(session_id):
    serve_ui(session_id)


def entrypoint():
    """The entry that the CLI is executed from"""

    try:
        import cowboy.logger

        # TODO: we should make a note that currently only supporting
        # running a single repo-at-a-time usage, due to hb and error file conflicts
        runner = Manager(config.HB_PATH, config.HB_INTERVAL)
        cowboy_cli()
    except CowboyClientError as e:
        click.secho(
            f"CowboyClientError: {e}",
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
