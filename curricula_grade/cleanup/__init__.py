from dataclasses import dataclass

from ..grader.task import Result, Error
from ..grader.task.profile import TaskProfile


@dataclass
class CleanupResult(Result):
    """Deletion of files, deallocation, etc."""

    kind = "cleanup"

    def __init__(self, passing: bool = True, complete: bool = True, error: Error = None, **details):
        super().__init__(complete=complete, passing=passing, error=error, details=details)


class Cleanup(TaskProfile):
    graded = False
    result_type = CleanupResult

