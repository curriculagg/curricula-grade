import abc

from ...grader.task import Result, Error
from .. import Test


class CorrectnessResult(Result):
    """The result of a correctness case."""

    kind = "correctness"

    def __init__(self, passing: bool, complete: bool = True, error: Error = None, **details):
        super().__init__(complete=complete, passing=passing, error=error, details=details)


class CorrectnessTest(Test, abc.ABC):
    """Override annotation."""

    result_type = CorrectnessResult
