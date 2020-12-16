from curricula_grade.grader.task import Task, Dependencies, Result, Error


class MockResult(Result):
    kind = "mock"

    def __init__(self, complete: bool = True, passing: bool = True, error: Error = None, details: dict = None):
        super().__init__(complete=complete, passing=passing, error=error, details=details)


def runnable() -> MockResult:
    return MockResult()


def task(name: str, **details):
    """Generate a task with some defaults already provided."""

    defaults = dict(
        description="A task",
        dependencies=Dependencies(set(), set()),
        runnable=runnable(),
        details=dict(),
        graded=True,
        points=None,
        weight=None,
        source="testing",
        tags=set(),
        result_type=Result)
    details["dependencies"] = Dependencies.from_details(details)
    defaults.update(details)
    return Task(name=name, **defaults)
