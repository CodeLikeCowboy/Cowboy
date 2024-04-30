from dataclasses import dataclass, field
from typing import Dict
from enum import Enum
from typing import List, Tuple, Any


class TaskStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class FunctionArg:
    name: str
    path: str


@dataclass
class PatchFile:
    path: str
    patch: str


@dataclass
class Task:
    repo_name: str
    task_id: str
    result: Dict
    status: str
    args: Any


@dataclass
class RunnerArgs:
    exclude_tests: List[Tuple[FunctionArg, str]]
    include_tests: List[str]
    patch_file: PatchFile


@dataclass
class RunnerTask(Task):
    args: RunnerArgs
