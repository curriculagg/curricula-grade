from typing import Set, Optional, Iterable
from dataclasses import dataclass

from . import Task
from .collection import TaskCollection
from .dependency import flatten_dependencies
from ...resource import Context


@dataclass(eq=False, init=False)
class TaskFilter:
    """Small helper to check whether a task should be run."""

    tags: Optional[Set[str]] = None
    task_names: Optional[Set[str]] = None
    related_task_names: Optional[Set[str]] = None

    def __init__(self, tasks: TaskCollection, context: Context, problem_short: str):
        """Build from context."""

        filtered_tags = context.options.get("tags")
        if filtered_tags is not None:
            self.tags = self.filter_problem_specific(filtered_tags, problem_short)

        # Assemble all tasks and dependencies
        filtered_task_names = context.options.get("tasks")
        if filtered_task_names is not None:
            self.task_names = self.filter_problem_specific(filtered_task_names, problem_short)

            # We also need to pull all dependencies
            self.related_task_names = set()
            task_lookup = {task.name: task for task in tasks}
            for filtered_task_name in self.task_names:
                for related_task_name in flatten_dependencies(filtered_task_name, task_lookup):
                    self.related_task_names.add(related_task_name)

    def __call__(self, task: Task) -> bool:
        """Check if a task should be run."""

        if self.tags is not None:
            if self.tags.isdisjoint(task.tags):
                return False
        if self.task_names is not None:
            if task.name not in self.task_names and task.name not in self.related_task_names:
                return False
        return True

    @property
    def has_effect(self) -> bool:
        return self.tags is not None or self.task_names is not None

    @staticmethod
    def filter_problem_specific(collection: Iterable[str], prefix: str) -> Set[str]:
        """Filter in items prefaced by prefix:xyz as xyz."""

        result = set()
        for item in collection:
            if ":" in item:
                if item.startswith(f"{prefix}:"):
                    result.add(item.split(":", maxsplit=1)[1])
            else:
                result.add(item)
        return result
