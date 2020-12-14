from ..grader.task import Result, Error
from ..grader.task.profile import TaskProfile


class SetupResult(Result):
    """Common result for generic tasks."""

    kind = "generic"

    def __init__(self, passing: bool = True, complete: bool = True, error: Error = None, **details):
        super().__init__(complete=complete, passing=passing, error=error, details=details)


class Setup(TaskProfile):
    graded = False
    result_type = SetupResult
