from typing import Union, List
from decimal import Decimal

from ..grader.task import Result, Error, Message


class CleanupResult(Result):
    """Deletion of files, deallocation, etc."""

    def __init__(
            self,
            passing: bool,
            complete: bool = True,
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

