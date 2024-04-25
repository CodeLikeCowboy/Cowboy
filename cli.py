import click
import yaml
from pathlib import Path
import sys

from src.repo.models import RepoConfig, RepoConfigRepository, PythonConf
from src.repo.repo import create_repo, delete_repo
from src.db.core import Database
from src.http.base import APIClient
from src.exceptions import CowboyClientError

from src.config import SAD_KIRBY, REPO_ROOT

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


# TODO: handle naming conflicts ...
@cowboy_repo.command("create")
@click.argument("config")
def repo_init(config):
    """Initializes a new repo."""

    with open(config, "r") as f:
        repo_config = yaml.safe_load(f)

    _, repo_name = owner_name_from_url(repo_config["url"])

    config_path = Path(config)
    if not config_path.exists():
        click.secho("Config file does not exist.", fg="red")
        return

    exists = rc_repo.find(repo_name)
    if exists:
        click.secho("Overwriting config for existing repo", fg="yellow")

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
        forked_url="",
        cloned_folders=[],
        source_folder="",
        python_conf=python_conf,
    )

    # call API to get forked_url first
    res = api.post("/repo/create", repo_config.serialize())
    forked_url = res.get("forked_url", "")
    repo_config.forked_url = forked_url

    # update conf with cloned folder paths
    updated_conf = create_repo(repo_config, Path(REPO_ROOT), db.get("num_repos"))

    rc_repo.save(updated_conf)

    click.secho(
        "Successfully created repo: {}".format(updated_conf.repo_name), fg="green"
    )


@cowboy_repo.command("baseline")
@click.argument("repo_name")
def repo_baseline(repo_name):
    pass


@cowboy_repo.command("delete")
@click.argument("repo_name")
def delete(repo_name):
    """
    Deletes all repos and reset the database
    """
    if not rc_repo.find(repo_name):
        click.secho(f"No such repo {repo_name}", fg="red")
        sys.exit(1)

    rc_repo.delete(repo_name)
    delete_repo(Path(REPO_ROOT), repo_name)
    api.delete(f"/repo/delete/{repo_name}")


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
