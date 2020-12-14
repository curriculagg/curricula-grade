from typing import Set, Iterable, Iterator

from .collection import TaskCollection
from .dependency import flatten_dependencies
from ...resource import Context

__all__ = ("filter_tasks",)


def filter_problem_specific(prefix: str, collection: Iterable[str]) -> Set[str]:
    """Filter in items prefaced by prefix:xyz as xyz."""

    result = set()
    for item in collection:
        if ":" in item:
            if item.startswith(f"{prefix}:"):
                result.add(item.split(":", maxsplit=1)[1])
        else:
            result.add(item)
    return result


def filter_tasks_by_tag(tags: Set[str], problem_short: str, tasks: TaskCollection) -> Iterator[str]:
    """Return a set of task names by tag."""

    tags = filter_problem_specific(problem_short, tags)
    for task in tasks:
        if not tags.isdisjoint(task.tags):
            yield task.name


def filter_tasks_by_name(names: Set[str], problem_short: str, tasks: TaskCollection) -> Iterator[str]:
    """Filter by name match."""

    names = filter_problem_specific(problem_short, names)

    # Allow wildcard to group by problem
    if "*" in names:
        for task in tasks:
            yield task.name

    # Normal filter
    else:
        for task in tasks:
            if task.name in names:
                yield task.name


def filter_tasks(context: Context, problem_short: str, tasks: TaskCollection) -> Set[str]:
    """Check if a task should be run."""

    if context.task_tags is None and context.task_names is None:
        return set(task.name for task in tasks)

    task_names = set()
    if context.task_tags is not None:
        task_names |= set(filter_tasks_by_tag(context.task_tags, problem_short, tasks))
    if context.task_names is not None:
        task_names |= set(filter_tasks_by_name(context.task_names, problem_short, tasks))

    # Add dependencies
    task_lookup = {task.name: task for task in tasks}
    for task_name in task_names.copy():
        for dependency_task_name in flatten_dependencies(task_name, task_lookup):
            task_names.add(dependency_task_name)

    return task_names
