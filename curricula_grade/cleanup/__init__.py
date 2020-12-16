from dataclasses import dataclass

from ..grader.task import Result, Error


@dataclass
class CleanupResult(Result):
    """Deletion of files, deallocation, etc."""

    def __init__(self, passing: bool = True, complete: bool = True, error: Error = None, **details):
        super().__init__(complete=complete, passing=passing, error=error, details=details)
