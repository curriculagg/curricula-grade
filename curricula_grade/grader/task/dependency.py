from typing import Iterator

from . import Task
from ...exception import GraderException
from ...grader.report import ProblemReport

from typing import Dict, List

__all__ = ("topological_sort", "fulfills_dependencies", "flatten_dependencies")


def topological_sort_visit(task: Task, lookup: Dict[str, Task], marks: Dict[Task, int], result: List[Task]):
    """Visit a node."""

    if marks[task] == 2:
        return

    if marks[task] == 1:
        raise GraderException("found cycle in task dependencies")

    marks[task] = 1
    for dependency in task.dependencies.passing | task.dependencies.complete:
        topological_sort_visit(lookup[dependency], lookup, marks, result)
    marks[task] = 2
    result.append(task)


def topological_sort(tasks: List[Task]):
    """Order tasks by dependency."""

    lookup = {}
    marks = {}
    result = []
    for task in tasks:
        marks[task] = 0
        lookup[task.name] = task
    for task in tasks:
        if marks[task] != 2:
            topological_sort_visit(task, lookup, marks, result)
    tasks.clear()
    tasks.extend(result)


def fulfills_dependencies(task: Task, report: ProblemReport):
    """Convenience."""

    return all((
        all(report.automated[dependency].passing for dependency in task.dependencies.passing),
        all(report.automated[dependency].complete for dependency in task.dependencies.complete)))


def flatten_dependencies(task_name: str, task_lookup: Dict[str, Task]) -> Iterator[str]:
    """Return a flattened iterable of dependencies task names."""

    for related_task_name in task_lookup[task_name].dependencies.all():
        yield related_task_name
        yield from flatten_dependencies(related_task_name, task_lookup)
