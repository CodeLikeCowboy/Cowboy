import os
import tempfile
import hashlib
from pathlib import Path
from logging import getLogger
from git import Repo, GitCommandError
from dataclasses import dataclass

import random
from typing import List, Union

logger = getLogger("test_results")


class GitRepo:
    """
    Used to manage git operations on a git repo
    """

    def __init__(self, repo_path: Path):
        if not repo_path.exists():
            # test suite may be renamed or deleted
            raise Exception("GitRepo does not exist: ", repo_path)

        # used for reversing patches
        self.patched_files = {}
        self.repo_folder = repo_path
        self.repo = Repo(repo_path)
        self.head = self.repo.head

    def commit_exists(self, commit_sha: str) -> bool:
        """
        Checks if a commit exists in the repo
        """
        try:
            self.repo.commit(commit_sha)
            return True
        except Exception:
            return False

    def get_curr_commit(self):
        """
        Returns the current commit sha
        """
        return self.head.commit.hexsha

    def reset_to_commit(self, commit_sha, parent=None):
        """
        Resets the index of the repository to a specific commit.
        """
        self.repo.git.reset("--hard", commit_sha)
        return f"Successfully reset to commit {commit_sha}"

    def get_prev_commit(self, commit_sha):
        """
        Returns the previous commit of a given commit sha
        """
        return self.repo.commit(commit_sha).parents[0]

    def apply_patch(self, patch: str) -> None:
        """
        Applies a patch from a .diff file to a single file in the repository
        """
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as patch_file:
            patch_file.write(patch.encode("utf-8") + b"\n")
            patch_file.flush()

        patch_hash = hashlib.md5(patch.encode("utf-8")).hexdigest()
        self.repo.git.apply(patch_file.name, whitespace="nowarn")
        self.patched_files[patch_hash] = patch_file.name

        # with tempfile.NamedTemporaryFile(
        #     mode="w+t", encoding="utf-8", delete=False
        # ) as patch_file:
        #     patch_file.write(patch)
        #     patch_file.flush()

        # with open("patch_file", "w", encoding="utf-8") as f:
        #     f.write(patch)

        # patch_hash = hashlib.md5(patch.encode()).hexdigest()
        # self.repo.git.apply(patch_file.name, whitespace="nowarn")
        # self.patched_files[patch_hash] = patch_file.name

    def reverse_patch(self, patch: str) -> None:
        """
        Reverses a patch from a .diff
        """
        patch_hash = hashlib.md5(patch.encode()).hexdigest()
        patch_file = self.patched_files[patch_hash]

        self.repo.git.apply(patch_file, reverse=True)
        self.patched_files.pop(patch_hash)


class PatchApplyExcepion(Exception):
    pass


class IncompatibleCommit(Exception):
    pass


# TODO: add __str__ and then use str() in method
@dataclass
class PatchFile:
    path: Path
    patch: str


class PatchFileContext:
    """
    Context manager for applying and reversing patches
    """

    def __init__(
        self, repo: GitRepo, patch: Union[str, PatchFile], revert: bool = True
    ):

        self.repo = repo
        self.patch = patch
        # assume all cases repo and patch are both specified, or neither are
        self.head_commit = self.repo.head.commit if self.patch else None
        self.failed_id = random.randint(0, 1000000)
        # for debugging
        self.revert = revert

    # def _write_broken_patch(self):
    #     with open(
    #         f"log/failed_patches/patch_{self.failed_id}.diff", "w+", encoding="utf-8"
    #     ) as f:
    #         f.write(self.patch)

    def __enter__(self):
        if not self.patch:
            return

        try:
            if isinstance(self.patch, PatchFile):
                with open(self.patch.path, "w", encoding="utf-8") as f:
                    f.write(self.patch.patch)
            elif isinstance(self.patch, str):
                self.repo.apply_patch(self.patch)

        except GitCommandError as e:
            # self._write_broken_patch()
            raise PatchApplyExcepion(e)

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.patch:
            return

        try:
            if isinstance(self.patch, PatchFile) and self.revert:
                self.repo.reset_to_commit(self.head_commit)
            elif isinstance(self.patch, str) and self.revert:
                self.repo.reverse_patch(self.patch)

        except GitCommandError as e:
            logger.info(f"Error reversing patch")
            raise PatchApplyExcepion(e)


class RepoCommitContext:
    """
    Resets the repository to a specific commit
    """

    def __init__(self, repo: GitRepo, fd_reset: bool = False, revert: bool = True):
        self.repo = repo
        self.revert = revert
        self.fd_reset = fd_reset

    def __enter__(self):
        """
        Saves the current commit hash when entering the context.
        """
        self.original_commit = self.repo.head.commit.hexsha
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Restores the repository to the original commit when exiting the context.
        """
        if exc_type is not None:
            print(f"An exception occurred: {exc_type.__name__}: {exc_value}")
            # Optionally, log the traceback here

        if self.fd_reset:
            self._add_files()

        if self.original_commit and self.revert:
            self.repo.reset_to_commit(self.original_commit)

        # reset the patched files in GitRepo
        self.repo.patched_files = {}

    def _add_files(self):
        """
        Adds all files in repo so that they are tracked by git and can be resetted
        when the context is exited
        """
        self.repo.repo.git.add(".")
        print(self.repo.repo.git.status())

    def reset_to_commit(self, commit_sha: str, parent=None):
        """
        Resets the index of the repository to a specific commit.
        """
        return self.repo.reset_to_commit(commit_sha, parent)
