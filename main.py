import click
import yaml
from pathlib import Path

from src.repo.models import RepoConfig, RepoConfigRepository, PythonConf
from src.db.core import Database

db = Database()

# init <repo_name> <config>


def owner_name_from_url(url: str):
    owner, repo_name = url.split("/")[-2:]
    return owner, repo_name


@click.group()
def cowboy_cli():
    """Command-line interface to Cowboy."""
    pass


@cowboy_cli.group("repo")
def cowboy_repo():
    """Container for all repo commands."""
    pass


@cowboy_repo.command("init")
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

    py_conf = PythonConf(
        cov_folders=repo_config.get("cov_folders", []),
        test_folder=repo_config.get("test_folder", ""),
        interp=repo_config.get("interp", ""),
        pythonpath=repo_config.get("pythonpath", ""),
    )

    repo_config = RepoConfig(
        repo_name=owner + "_" + repo_name,
        url=repo_config.get("url"),
        forked_url="",
        cloned_folders=[],
        source_folder="",
        py_confg=py_conf,
    )

    rc_repo.save(repo_config)
    click.secho("Success.", fg="green")


def entrypoint():
    """The entry that the CLI is executed from"""

    try:
        cowboy_cli()
    except Exception as e:
        import traceback

        tb = traceback.format_exc()

        click.secho(f"ERROR: {e}\n{tb}", bold=True, fg="red")


if __name__ == "__main__":
    entrypoint()
