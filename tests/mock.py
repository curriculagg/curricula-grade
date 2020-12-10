from curricula_grade.task import Task, Dependencies, Result, Error


class MockResult(Result):
    def __init__(self, complete: bool = True, passing: bool = True, error: Error = None, details: dict = None):
        super().__init__(complete=complete, passing=passing, error=error, details=details)


def task(name: str, **details):
    """Generate a task with some defaults already provided."""

    defaults = dict(
        description="A task",
        kind="unit",
        dependencies=Dependencies(set(), set()),
        runnable=lambda: MockResult(),
        details=dict(),
        weight=1,
        source="testing",
        tags=set(),
        result_type=MockResult)
    details["dependencies"] = Dependencies.from_details(details)
    defaults.update(details)
    return Task(name=name, **defaults)
