from ..grader.task import Result, Error


class SetupResult(Result):
    """Common result for generic tasks."""

    def __init__(self, passing: bool = True, complete: bool = True, error: Error = None, **details):
        super().__init__(complete=complete, passing=passing, error=error, details=details)
