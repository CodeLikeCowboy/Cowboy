import click
import yaml
from pathlib import Path
import sys

from src.repo.models import RepoConfig, RepoConfigRepository, PythonConf
from src.repo.repo import RepoTestContext, RepoTestContextFactory
from src.db.core import Database
from src.http.base import APIClient
from src.exceptions import CowboyClientError
from src.config import SAD_KIRBY


db = Database()
api = APIClient(db)


def owner_name_from_url(url: str):
    owner, repo_name = url.split("/")[-2:]
    return owner, repo_name


@click.group()
def cowboy_cli():
    """Command-line interface to Cowboy."""
    pass


@cowboy_cli.command("init")
@click.argument("email")
@click.argument("password")
def init(email, password):
    """Initializes user account for Cowboy."""

    res = api.post("/register", {"email": email, "password": password})
    if res.status_code == 200:
        click.secho("Successfully registered user", fg="green")


@cowboy_cli.group("repo")
def cowboy_repo():
    """Container for all repo commands."""
    pass


@cowboy_repo.command("create")
@click.argument("repo_name")
@click.argument("config")
def repo_init(repo_name, config):
    """Initializes a new repo."""

    click.echo("Initializing new repo {}".format(repo_name))
    config_path = Path(config)
    if not config_path.exists():
        click.secho("Config file does not exist.", fg="red")
        return

    with open(config_path, "r") as f:
        repo_config = yaml.safe_load(f)

    rc_repo = RepoConfigRepository(db)
    owner, repo_name = owner_name_from_url(repo_config["url"])

    python_conf = PythonConf(
        cov_folders=repo_config.get("cov_folders", []),
        test_folder=repo_config.get("test_folder", ""),
        interp=repo_config.get("interp"),
        pythonpath=repo_config.get("pythonpath", ""),
    )

    repo_config = RepoConfig(
        repo_name=owner + "_" + repo_name,
        url=repo_config.get("url"),
        forked_url="",
        cloned_folders=[],
        source_folder="",
        python_conf=python_conf,
    )

    # TODO: pop command to ask user if they want to overwrite
    exists = rc_repo.find(repo_config.repo_name)
    if exists:
        click.secho("Overwriting config for existing repo", fg="yellow")

    # res = api.post("/repo/create", repo_config.serialize())
    # forked_url = res["forked_url"]
    # repo_config.forked_url = forked_url
    rc_repo.save(repo_config)

    click.secho(
        "Successfully created repo: {}".format(repo_config.repo_name), fg="green"
    )


@cowboy_repo.command("baseline")
@click.argument("repo_name")
def repo_baseline(repo_name):
    repo_ctxt = RepoTestContextFactory(db).create_context(repo_name, verify=True)


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
