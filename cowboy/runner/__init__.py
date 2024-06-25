from .python import PytestDiffRunner
from .base import TestSuiteError, RunnerError

runners = {"python": PytestDiffRunner}
