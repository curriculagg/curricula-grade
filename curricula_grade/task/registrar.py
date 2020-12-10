import functools
from typing import List, Type, Optional, Callable
from decimal import Decimal

from curricula.library.debug import get_source_location

from . import Task, Runnable, Dependencies, Result
from .exception import GraderException
from .collection import TaskCollection

from ..build import BuildResult
from ..check import CheckResult
from ..cleanup import CleanupResult
from ..test.code import CodeResult
from ..test.correctness import CorrectnessResult
from ..test.complexity import ComplexityResult
from ..test.memory import MemoryResult


RegistrarDecorator = Callable[[Runnable], Runnable]
RegistrarCallable = Callable[[Runnable, dict], Runnable]


class RegistrarEndpoint:
    """Generates a function for a specific task."""

    result_type: Type[Result]

    def __init__(self, _register, result_type: Type[Result]):
        """Cache base registrar and result_type."""

        self._register = _register
        self.result_type = result_type

    def __call__(self, **details) -> Optional[RegistrarDecorator]:
        """Register a runnable or ask for a decorator."""

        # If details were passed, explode into details
        inner_details = details.pop("details", {})
        details.update(inner_details)

        # Check if we were passed a runnable in kwargs
        runnable = details.pop("runnable", None)
        if runnable is not None:
            self._register(runnable=runnable, details=details, result_type=self.result_type)
            return None

        return functools.partial(self._register, details=details, result_type=self.result_type)


class Registrar:
    """Utility class for registering tasks."""

    tasks: TaskCollection

    def __init__(self, tasks: TaskCollection):
        self.tasks = tasks

    def _register(self, runnable: Runnable, details: dict, result_type: Type[Result]):
        """Wrap the runnable as a task and add it to the grader."""

        name = details.pop("name", None)
        if name is None:
            name = getattr(runnable, "__qualname__", None)
            if name is None:
                raise GraderException("No viable candidate for task name, please provide during registration")

        description = details.pop("description", None) or runnable.__doc__
        graded = details.pop("graded", True)
        weight = Decimal(details.pop("weight", 1))
        dependencies = Dependencies.from_details(details)

        tags = details.pop("tags", None)
        if tags is None:
            tags = set()
        elif not isinstance(tags, set):
            raise GraderException(f"Tags must be a set or None")

        for existing_task in self.tasks:
            if existing_task.name == name:
                raise GraderException(f"Duplicate task name \"{name}\"")

        # Create task, append
        self.tasks.push(Task(
            name=name,
            description=description,
            kind=result_type.kind,
            dependencies=dependencies,
            runnable=runnable,
            details=details,
            weight=weight,
            source=get_source_location(2),
            tags=tags,
            graded=graded,
            result_type=result_type))
        return runnable

    def __getitem__(self, result_type: Type[Result]) -> RegistrarCallable:
        """Allow use of custom result types."""

        return functools.partial(self._register, result_type=result_type)

    build = RegistrarEndpoint(_register=_register, result_type=BuildResult)
    check = RegistrarEndpoint(_register=_register, result_type=CheckResult)
    cleanup = RegistrarEndpoint(_register=_register, result_type=CleanupResult)
    code = RegistrarEndpoint(_register=_register, result_type=CodeResult)
    correctness = RegistrarEndpoint(_register=_register, result_type=CorrectnessResult)
    complexity = RegistrarEndpoint(_register=_register, result_type=ComplexityResult)
    memory = RegistrarEndpoint(_register=_register, result_type=MemoryResult)
