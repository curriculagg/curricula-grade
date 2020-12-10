from curricula_grade.task import Task, Dependencies, Result as _Result
from curricula_grade.task.error import Error


class Result(_Result):
    kind = "mock"

    def __init__(self, complete: bool = True, passing: bool = True, error: Error = None, details: dict = None):
        super().__init__(complete=complete, passing=passing, error=error, details=details)


def runnable():
    return Result()


def task(name: str, **details):
    """Generate a task with some defaults already provided."""

    defaults = dict(
        description="A task",
        kind="unit",
        dependencies=Dependencies(set(), set()),
        runnable=runnable(),
        details=dict(),
        graded=True,
        weight=1,
        source="testing",
        tags=set(),
        result_type=Result)
    details["dependencies"] = Dependencies.from_details(details)
    defaults.update(details)
    return Task(name=name, **defaults)
