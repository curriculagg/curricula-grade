from ...grader.task import Result, Error
from ...grader.task.profile import TaskProfile


class CorrectnessResult(Result):
    """The result of a correctness case."""

    kind = "correctness"

    def __init__(self, passing: bool, complete: bool = True, error: Error = None, **details):
        super().__init__(complete=complete, passing=passing, error=error, details=details)


class Correctness(TaskProfile):
    result_type = CorrectnessResult
