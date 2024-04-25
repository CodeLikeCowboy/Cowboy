from typing import NamedTuple, Optional, List, Dict, Iterable, Tuple
from pathlib import Path
import json
from itertools import product

from logging import getLogger

logger = getLogger("test_results")


class CoverageException(Exception):
    pass


class CoverageFailure(Exception):
    pass


class CoverageSubtractionError(Exception):
    def __init__(self):
        super().__init__("Negative covered but contributed covered_lines")


# Refactor: create a CoverageBuilder class that supports parsing different coverage report formats
class Coverage:
    def __init__(
        self,
        filename: str,
        covered_lines: List[int],
        missing_lines: List[int],
    ):
        self.all_lines = covered_lines + missing_lines
        assert len(self.all_lines) == len(set(self.all_lines))

        # self.cov: int = cov
        self.covered_lines: List[int] = covered_lines
        self.missing_lines: List[int] = missing_lines

        self.stmts: int = len(self.all_lines)
        self.misses: int = len(self.missing_lines)
        self.covered: int = len(self.covered_lines)

        if covered_lines and missing_lines:
            for line in covered_lines:
                if line in missing_lines:
                    raise CoverageException(
                        f"Line {line} is both covered and missing in {filename}"
                    )

        self.filename: str = filename

        # defer initialization
        self._covered_lines_dict: Dict[int, str] = {}
        self._miss_lines_dict: Dict[int, str] = {}

    @property
    def cov(self) -> float:
        return self.covered / self.stmts

    def __eq__(self, other: Optional["Coverage"]):
        # None comparison
        if not other:
            if (
                self.filename == None
                and self.stmts == None
                and self.misses == None
                and self.covered == None
                and self.cov == None
            ):
                return True
            return False

        elif isinstance(other, Coverage):
            if (
                self.filename == other.filename
                and self.stmts == other.stmts
                and self.misses == other.misses
                and self.covered == other.covered
                and self.cov == other.cov
            ):
                return True
            return False

        else:
            raise CoverageException("Comparisons only allowed for Coverage or None")

    def __sub__(self, other: "Coverage"):
        try:
            assert isinstance(other, Coverage)
            assert self.filename == other.filename
            # may be from another commit
            assert self.stmts == other.stmts
            # TODO: put a check here against whether the covered_lines
            # match up
        except AssertionError as e:
            raise CoverageException(f"Assertion failed: {e}")

        # NOTE:
        # use set sub here to find only the overlapping missing lines
        # for eg.
        # a_miss = [1,2,3]
        # b_miss = [1,2,4]
        # if we just sub the abs len of missing lines, we would get:
        # a_miss - b_miss = []
        # but instead we want:
        # a_miss - b_miss = [3]
        # Because we want to if b improved the coverage of a
        added_lines = set(self.covered_lines) - set(other.covered_lines)
        missing_lines = set(self.all_lines) - added_lines

        cov = Coverage(
            self.filename,
            covered_lines=list(added_lines),
            missing_lines=list(missing_lines),
        )
        # need to do this to support negative coverage
        cov.covered = self.covered - other.covered
        if cov.covered < 0 and cov.covered_lines:
            # theoretically shud not happen, except in case
            # where a covered test causes another test to fail
            raise CoverageSubtractionError

        return cov

    def __add__(self, other: "Coverage"):
        """
        Unlike sub, we can only add the covered from other if it does not overlap
        with a pre-exsiting line
        """
        try:
            assert isinstance(other, Coverage)
            assert self.filename == other.filename
            # may be from another commit
            assert self.stmts == other.stmts
        except AssertionError as e:
            raise CoverageException(f"Assertion failed: {e}")

        added_lines = set(other.covered_lines) - set(self.covered_lines)
        missing_lines = set(self.all_lines) - set(self.covered_lines) - added_lines

        return Coverage(
            self.filename,
            covered_lines=list(set(self.covered_lines).union(added_lines)),
            missing_lines=list(missing_lines),
        )

    # COVREFACTOR:
    @classmethod
    def diff_cov(cls, a: "Coverage", b: "Coverage", keep_line: int) -> "Coverage":
        """
        Gets the diff between two coverages that also includes covered_lines
        """
        assert keep_line in [1, 2]

        cov_diff = a - b

        sub1 = set(a.covered_lines) if keep_line == 1 else set(b.covered_lines)
        sub2 = set(b.covered_lines) if keep_line == 1 else set(a.covered_lines)
        if len(sub1) < len(sub2):
            logger.warn("a < b in the subtraction of covered lines, is this expected?")

        covered_lines = sub1 - sub2
        cov_diff.covered_lines = covered_lines
        return cov_diff

    def __str__(self):

        return f"Coverage: {self.filename}, stmts: {self.stmts}, misses: {self.misses}, covered: {self.covered}"

    def read_line_contents(self, base_path: Path = None):
        """
        Lazily reads the line contents of the file
        """
        fp = base_path / self.filename if base_path else self.filename
        with open(fp, "r", encoding="utf-8") as file:
            # print("Covered lines: ", self.covered_lines)
            all_lines = ""
            for i, line in enumerate(file.read().split("\n"), start=1):
                all_lines += f"{i}. {line}" + "\n"
                if i in self.covered_lines:
                    self._covered_lines_dict[i] = line
                elif i in self.missing_lines:
                    self._miss_lines_dict[i] = line

    def print_lines(self, line_type: str = "covered"):
        lines_dict = (
            self._covered_lines_dict
            if line_type == "covered"
            else self._miss_lines_dict
        )

        repr = ""
        repr += f"{line_type} lines in :: {self.filename}\n"
        for k, v in lines_dict.items():
            repr += f"{k}: {v}\n"

        return repr

    def get_contiguous_lines(self) -> Iterable[List[Tuple[int, str]]]:
        """
        Returns a list of contiguous line groups
        """
        from itertools import groupby

        for k, g in groupby(
            enumerate(self._covered_lines_dict.items()), lambda ix: ix[1][0] - ix[0]
        ):
            yield [x for _, x in g]

    def serialize(self):
        return {
            "filename": self.filename,
            "covered_lines": self.covered_lines,
            "missing_lines": self.missing_lines,
        }

    @classmethod
    def deserialize(self, data) -> "Coverage":
        return Coverage(data["filename"], data["covered_lines"], data["missing_lines"])


class NoCoverageDB(Exception):
    pass


class TestCoverage:
    """
    Coverage for a list of files from a commit
    """

    def __init__(
        self,
        cov_list: List[Coverage],
        isdiff: bool = False,
    ):
        self.isdiff = isdiff
        self.filenames = [cov.filename for cov in cov_list]

        self._cov_list = cov_list

        total_misses = 0
        total_stmts = 0
        total_covered = 0
        for coverage in cov_list:
            total_misses += coverage.misses
            total_stmts += coverage.stmts
            total_covered += coverage.covered

        self.total_cov = Coverage("TOTAL", [], [])
        self.total_cov.misses = total_misses
        self.total_cov.stmts = total_stmts
        self.total_cov.covered = total_covered

    @property
    def cov_list(self):
        return [cov for cov in self._cov_list if cov.filename != "TOTAL"]

    # @classmethod
    # def from_coverage_report(cls, stdout: str) -> "TestCoverage":
    #     import re

    #     pattern = re.compile(r"(\S+)\s+(\d+)\s+(\d+)\s+(\d+)%")

    #     lines = stdout.split("\n")
    #     parsed_results = []

    #     for line in lines:
    #         match = pattern.search(line)
    #         if match:
    #             # Extract the filename, stmts, misses, and coverage
    #             filename = match.group(1)
    #             stmts = int(match.group(2))
    #             misses = int(match.group(3))
    #             cov = int(match.group(4))

    #             parsed_results.append(Coverage(filename, stmts, misses))

    #     return TestCoverage(parsed_results)

    # This method will be implemented by other languages, make it mixin or something
    @classmethod
    def from_coverage_file(cls, coverage_json: dict) -> "TestCoverage":
        cov_list = []
        # add exception catcher here for missing json
        try:
            for filename, data in coverage_json["files"].items():
                cov_list.append(
                    Coverage(
                        filename,
                        data["executed_lines"],
                        data["missing_lines"],
                    )
                )
        except FileNotFoundError:
            logger.info("Coverage file not found")
            return cls([])

        return cls(cov_list)

    @classmethod
    def diff_cov(
        cls, a: "TestCoverage", b: "TestCoverage", keep_line: int
    ) -> "TestCoverage":
        """
        Used for subtracting two TestCoverages when we also want to diff their covered_lines
        keep_line parameter is introduced to control the order of the set subtraction
        """
        if keep_line not in [1, 2]:
            raise ValueError("keep_line must be 1 or 2")

        cov_list = []
        for a, b in zip(a.cov_list, b.cov_list):
            cov_diff = Coverage.diff_cov(a, b, keep_line)
            cov_list.append(cov_diff)

        return cls(cov_list, isdiff=True)

    def get_file_cov(self, filename: Path, base_path: Path) -> Optional[Coverage]:
        """
        Gets a file coverage by filename. Base_path required because coverage file paths are relative
        to the repo_path as root
        """
        try:
            return next(
                filter(
                    lambda x: (
                        x.filename
                        if not base_path
                        else base_path / x.filename == filename
                    ),
                    self.cov_list,
                )
            )
        except StopIteration:
            return None

    def __bool__(self):
        return self.cov_list != []

    def __iter__(self):
        return iter([cov for cov in self.cov_list if cov.filename != "TOTAL"])

    def is_zero(self):
        return self.total_cov.misses == 0

    def __sub__(self, other: "TestCoverage") -> "TestCoverage":
        """
        Take the difference of every matching file coverage plus our own coverage
        that is not matched by other and that is nonzero
        """
        a, b = self.cov_list, other.cov_list

        merged_list = []
        a_only_cov = [a for a in a if a.filename not in [b.filename for b in b]]
        intersect_fp = [i.filename for i in a if i.filename in [b.filename for b in b]]

        for cov_a, cov_b in product(a, b):
            if cov_a.filename == cov_b.filename and cov_a.filename in intersect_fp:
                cov_diff = cov_a - cov_b
                if cov_diff.covered != 0:
                    merged_list.append(cov_diff)

        return TestCoverage(merged_list + a_only_cov, isdiff=True)

    def __add__(self, other: "TestCoverage") -> "TestCoverage":
        """
        Take add to our existing coverage only those lines that are not covered by ours
        """
        a, b = self.cov_list, other.cov_list

        merged_list = []
        a_only_cov = [a for a in a if a.filename not in [b.filename for b in b]]
        b_only_cov = [b for b in b if b.filename not in [a.filename for a in a]]
        intersect_fp = [i.filename for i in a if i.filename in [b.filename for b in b]]

        for cov_a, cov_b in product(a, b):
            if cov_a.filename == cov_b.filename and cov_a.filename in intersect_fp:
                merged_list.append(cov_a + cov_b)

        return TestCoverage(a_only_cov + merged_list + b_only_cov, isdiff=True)

    def covered_lines(self) -> List[Tuple[str, List[int]]]:
        cov_lines = [(cov.filename, cov.covered_lines) for cov in self.cov_list]
        return cov_lines

    def missing_lines(self) -> List[Tuple[str, List[int]]]:
        cov_lines = [(cov.filename, cov.missing_lines) for cov in self.cov_list]
        return cov_lines

    # def did_improve(self) -> int:
    #     if not self.isdiff:
    #         raise CoverageException("Improvement can only be checked on a diff")

    #     # TODO: write a test for this
    #     return self.total_cov.covered

    def cov_list_str(self):
        return "\n".join([str(cov) for cov in self.cov_list])

    def __repr__(self):
        return f"TestCoverage: {self.total_cov}, IsDiff:{self.isdiff}"

    def serialize(self):
        return {
            "cov_list": [cov.serialize() for cov in self.cov_list],
            "isdiff": self.isdiff,
        }

    @classmethod
    def deserialize(self, data: List[List]) -> "TestCoverage":
        return TestCoverage(
            [Coverage(**lines) for lines in data["cov_list"]],
            isdiff=data["isdiff"],
        )
