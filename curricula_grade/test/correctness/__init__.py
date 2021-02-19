from typing import Any, Union, List
from decimal import Decimal

from ...grader.task import Result, Error, Message


class CorrectnessResult(Result):
    """The result of a correctness case."""

    expected: Any = None
    actual: Any = None

    def __init__(
            self,
            passing: bool,
            complete: bool = True,
            expected: Any = None,
            actual: Any = None,
            score: Union[Decimal, int, float, str] = None,
            error: Error = None,
            messages: List[Message] = None,
            details: dict = None):
        """Add fields for expected and actual."""

        super().__init__(
            passing=passing,
            complete=complete,
            score=score,
            error=error,
            messages=messages,
            details=details)
        self.expected = expected
        self.actual = actual

    def dump(self, thin: bool = False) -> dict:
        """Add extra details."""

        dump = super().dump()
        dump.update(expected=self.expected, actual=self.actual)
        return dump

    @classmethod
    def shorthand(
            cls,
            passing: bool = True,
            complete: bool = True,
            error: Error = None,
            actual: Any = None,
            expected: Any = None,
            **details) -> "CorrectnessResult":
        """Expand details."""

        return cls(
            complete=complete,
            passing=passing,
            error=error,
            actual=actual,
            expected=expected,
            details=details)
