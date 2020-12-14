import functools
from typing import Type, Any, Set, Optional
from decimal import Decimal

from curricula.library.debug import get_source_location

from . import Runnable, Task, Result, Dependencies
from .profile import TaskProfile
from .collection import TaskCollection
from ...exception import GraderException


def is_some(value: Any) -> bool:
    """Shorthand for checking if identical to None."""

    return value is not None


def first_some(*args: Any) -> Any:
    """Return the first arg that is not None."""

    try:
        return next(filter(None, args))
    except StopIteration:
        return None


def underwrite(source: dict, destination: dict) -> dict:
    """Fill keys in source not defined in destination."""

    for key, value in source.items():
        if key not in destination:
            destination[key] = value
    return destination


class TaskRegistrar:
    """Utility class for registering tasks."""

    tasks: TaskCollection

    def __init__(self):
        """Assign task collection and dynamically create shortcuts."""

        self.tasks = TaskCollection()

    def register(self, runnable: Any, details: dict, result_type: Type[Result] = Result):
        """Explicitly register a runnable."""

        self._register_with_result_type(runnable=runnable, details=details, result_type=result_type)

    def __getitem__(self, profile: Type[TaskProfile]):
        """Partial in the result_type."""

        def register(runnable: Runnable = None, /, **details: dict):
            """Return potentially a decorator or maybe not."""

            if runnable is not None:
                self._register_with_profile(runnable=runnable, details=details, profile=profile)
                return

            return functools.partial(self._register_with_profile, details=details, profile=profile)

        return register

    def _register_with_profile(self, runnable: Any, details: dict, profile: Type[TaskProfile]):
        tags = TaskRegistrar._resolve_tags(details)
        self.tasks.push(Task(
            name=TaskRegistrar._resolve_name(runnable, details),
            description=TaskRegistrar._resolve_description(runnable, details),
            dependencies=Dependencies.from_details(details),
            runnable=runnable,
            graded=first_some(details.pop("graded", None), profile.graded, True),
            weight=Decimal(first_some(details.pop("weight", None), profile.weight, 1)),
            points=Decimal(p) if is_some(p := first_some(details.pop("points", None), profile.points)) else None,
            source=get_source_location(1),
            tags=tags.union(profile.tags) if profile.tags is not None else tags,
            result_type=profile.result_type,
            details=underwrite(profile.details, details) if profile.details is not None else details,))

    def _register_with_result_type(self, runnable: Any, details: dict, result_type: Type[Result]):
        self.tasks.push(Task(
            name=TaskRegistrar._resolve_name(runnable, details),
            description=TaskRegistrar._resolve_description(runnable, details),
            dependencies=Dependencies.from_details(details),
            runnable=runnable,
            graded=details.pop("graded", True),
            weight=Decimal(details.pop("weight", 1)),
            points=Decimal(p) if is_some(p := details.pop("points", None)) else None,
            source=get_source_location(1),
            tags=TaskRegistrar._resolve_tags(details),
            result_type=result_type,
            details=details))

    def weight(self) -> Decimal:
        """Combined weight of all graded tasks."""

        return sum(map(lambda t: t.weight, filter(lambda t: t.graded, self.tasks)), Decimal(0))

    @staticmethod
    def _resolve_name(runnable: Runnable, details: dict) -> str:
        if is_some(name := details.pop("name", None)):
            return name
        if is_some(name := getattr(runnable, "__qualname__", None)):
            return name
        raise GraderException("No viable candidate for task name, please provide during registration")

    @staticmethod
    def _resolve_description(runnable: Runnable, details: dict) -> Optional[str]:
        return details.pop("description", None) or runnable.__doc__

    @staticmethod
    def _resolve_tags(details: dict) -> Set[str]:
        if isinstance(tags := details.pop("tags", set()), set):
            return tags
        raise GraderException("tags must either be a set of strings or None")
