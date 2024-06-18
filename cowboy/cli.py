import click
import yaml
from pathlib import Path
import json

from cowboy.repo.models import RepoConfig, RepoConfigRepository, PythonConf
from cowboy.repo.repo import create_cloned_folders, delete_cloned_folders
from cowboy.api_cmds import (
    api_build_tm_mapping,
    api_coverage,
    api_augment,
    api_register,
)
from cowboy.browser import serve_ui
from cowboy.exceptions import CowboyClientError
from cowboy import config

from cowboy.db.core import Database
from cowboy.db.public import init_react_env_vars
from cowboy.http import APIClient, InternalServerError

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


@cowboy_cli.command("dump")
def dump():
    """Dumps db.json for debugging."""
    print(db.get_all())


@cowboy_cli.group("user")
def cowboy_user():
    """Container for all user commands."""
    pass


# TODO: should we make initialization a user dialogue instead?
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
            "first delete the current user via 'cowboy delete_user'",
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
    for repo in db.get("repos", []):
        delete_cloned_folders(Path(config.REPO_ROOT), repo)

    # TODO: currently running into server error when deleting user from DB
    # due to table cascade issues
    try:
        api.get(f"/user/delete")
    except InternalServerError:
        pass

    db.reset()
    click.secho("Successfully reset user data", fg="green")


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

    # should we differentiate between timeout/requests.exceptions.ConnectionError?
    except Exception as e:
        click.secho(f"Repo creation failed on server: {e}", fg="red")
        click.secho(f"Rolling back repo creation", fg="red")

        db.delete_from_list("repos", repo_name)
        delete_cloned_folders(Path(config.REPO_ROOT), repo_name)
        return


@cowboy_repo.command("coverage")
@click.argument("repo_name")
def cmd_coverage(repo_name):
    api_coverage(repo_name)


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


@cowboy_repo.command("augment")
@click.argument("repo_name")
@click.option("--mode", default="auto")
@click.option("--files", required=False, multiple=True)
@click.option("--tms", required=False, multiple=True)
def augment(repo_name, mode, files, tms):
    """
    Augments existing test modules with new test cases
    """
    # TODO: we should allow both files and tms at same time
    if files and tms:
        raise Exception("Cannot specify both files and tms")
    elif files:
        mode = "file"
    elif tms:
        mode = "module"
    # this is the "first-time user" mode so we run build_mapping beforehand
    elif mode == "auto":
        if files or tms:
            raise Exception("Cannot specify file or tms when mode=auto")
        api_build_tm_mapping(repo_name, mode, [], [])
    elif not files and not tms:
        mode = "all"

    session_id = api_augment(repo_name, mode, files, tms)
    serve_ui(session_id)


@cowboy_repo.command("build_tm_mapping")
@click.argument("repo_name")
@click.option("--mode", default="auto")
@click.option("--files", required=False, multiple=True)
@click.option("--tms", required=False, multiple=True)
def build_tm_mapping(repo_name, mode, files, tms):
    """
    Builds the test module to source file mapping for ALL test_modules
    """
    # TODO: we should allow both files and tms at same time
    if files and tms:
        raise Exception("Cannot specify both files and tms")
    elif files:
        mode = "file"
    elif tms:
        mode = "module"
    # this is the "first-time user" mode so we run build_mapping beforehand
    elif not files and not tms:
        mode = "all"

    # api_build_tm_mapping(repo_name, mode, files, tms)
    api_build_tm_mapping(repo_name, "module", [], ["TestBitrise"])


@cowboy_cli.command("browser")
def browser():
    serve_ui("8ea7ba7c-d78b-4d63-9bc8-7297c8f2641c")


def entrypoint():
    """The entry that the CLI is executed from"""

    try:
        # TODO: we should make a note that currently only supporting
        # running a single repo-at-a-time usage, due to hb and error file conflicts
        # runner = Manager(config.HB_PATH, config.HB_INTERVAL)
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
