import functools
from typing import Type, Any, Set, Optional, Callable
from decimal import Decimal

from curricula.library.debug import get_source_location

from . import Runnable, Task, Result, Dependencies
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

    def __call__(self, runnable: Any = None, /, **details) -> Optional[Callable[[Runnable], None]]:
        """Explicitly register a runnable."""

        if runnable is not None:
            self.register(runnable=runnable, details=details, result_type=self._determine_result_type(runnable))
            return

        def register(r: Runnable, /):
            self.register(runnable=r, details=details, result_type=self._determine_result_type(r))
        return register

    def __getitem__(self, result_type: Type[Result]):
        """Partial in the result_type."""

        def register(runnable: Runnable = None, /, **details):
            """Return potentially a decorator or maybe not."""

            if runnable is not None:
                self.register(runnable=runnable, details=details, result_type=result_type)
                return

            return functools.partial(self.register, details=details, result_type=result_type)

        return register

    def register(self, runnable: Any, details: dict, result_type: Type[Result] = None):
        self.tasks.push(Task(
            name=TaskRegistrar._resolve_name(runnable, details),
            description=TaskRegistrar._resolve_description(runnable, details),
            dependencies=Dependencies.from_details(details),
            runnable=runnable() if isinstance(runnable, type) else runnable,
            graded=details.pop("graded", True),
            weight=Decimal(w) if is_some(w := details.pop("weight", None)) else None,
            points=Decimal(p) if is_some(p := details.pop("points", None)) else None,
            source=get_source_location(1),
            tags=TaskRegistrar._resolve_tags(details),
            result_type=self._determine_result_type(runnable, result_type),
            details=details))

    def weight(self) -> Decimal:
        """Combined weight of all graded tasks."""

        return sum(map(lambda t: t.weight or 1, filter(lambda t: t.graded, self.tasks)), Decimal(0))

    @staticmethod
    def _determine_result_type(runnable: Runnable, fallback: Type[Result] = None) -> Type[Result]:
        result_type_candidate = None
        if is_some(annotations := getattr(runnable, "__annotations__", None)):
            result_type_candidate = annotations.get("return")
        if result_type_candidate is None:
            result_type_candidate = getattr(runnable, "result_type", None)
        if result_type_candidate is None:
            result_type_candidate = fallback
        if result_type_candidate is None:
            raise GraderException("result type must be specified by return annotation or bracket notation")
        if not issubclass(result_type_candidate, Result):
            raise GraderException("annotated result type does not inherit from Result")
        return result_type_candidate

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
