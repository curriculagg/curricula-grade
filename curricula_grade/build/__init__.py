from dataclasses import dataclass

from ..task import Error, Result
from ..task.profile import TaskProfile


@dataclass(init=False, eq=False)
class BuildResult(Result):
    """Returned from a build task."""

    kind = "build"

    def __init__(self, passing: bool, complete: bool = True, error: Error = None, **details):
        super().__init__(complete=complete, passing=passing, error=error, details=details)


class Build(TaskProfile):
    graded = False
    result_type = BuildResult
