from typing import List, Iterator

from . import Task
from .dependency import topological_sort


class TaskCollection:
    """Task collection with convenience tools."""

    tasks: List[Task]

    def push(self, task: Task):
        """Sort dependencies."""

        self.tasks.append(task)
        topological_sort(self.tasks)

    def __init__(self):
        """Set tasks."""

        self.tasks = []

    def __iter__(self) -> Iterator[Task]:
        """Yield out of list."""

        yield from self.tasks
