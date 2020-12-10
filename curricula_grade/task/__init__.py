import abc
import inspect
from typing import Dict, TypeVar, Generic, Any, Type, Set
from dataclasses import dataclass, field
from decimal import Decimal

from curricula.log import log

from .error import Error
from ..exception import GraderException

__all__ = ("Result", "Dependencies", "Task", "Runnable", "Error")


@dataclass(init=False, eq=False)
class Result(Exception, abc.ABC):
    """The result of a test."""

    complete: bool
    passing: bool
    details: dict
    error: Error
    task: "Task" = field(init=False, repr=False)

    # Associated with the type
    kind: str = field(init=False, repr=False)

    def __init__(self, complete: bool, passing: bool, error: Error = None, details: dict = None):
        """Initialize a new result.

        Details are passed as a dictionary in order to avoid potential
        collisions with normal arguments.
        """

        self.complete = complete
        self.passing = passing
        self.error = error
        self.details = details or dict()

    def dump(self, thin: bool = False) -> dict:
        """Serialize the result for JSON."""

        dump = dict(
            complete=self.complete,
            passing=self.passing,
            kind=self.kind,
            error=self.error.dump(thin=thin) if self.error is not None else self.error,
            task=dict(
                name=self.task.name,
                description=self.task.description))
        if not thin:
            dump.update(details=self.details)
        return dump

    @classmethod
    def load(cls, data: dict, task: "Task") -> "Result":
        """Load a result from serialized."""

        data.pop("task")
        kind = data.pop("kind")
        error_data = data.pop("error")
        error = Error.load(error_data) if error_data is not None else None
        self = cls(**data, error=error)
        self.task = task
        self.kind = kind
        return self

    @classmethod
    def incomplete(cls):
        """Return a mock result if the task was not completed."""

        return cls(complete=False, passing=False)

    @classmethod
    def default(cls):
        """Called in special cases if no result is returned."""

        return cls(complete=True, passing=True)


TResult = TypeVar("TResult", bound=Result)


class Runnable(Generic[TResult]):
    """Runnable function that returns some kind of result."""

    def __call__(self, **kwargs) -> TResult:
        """The signature that will receive dependency injection."""


@dataclass(eq=False)
class Dependencies:
    """Task dependencies based on passing or completion."""

    passing: Set[str]
    complete: Set[str]

    def all(self) -> Set[str]:
        return self.passing.union(self.complete)

    @classmethod
    def normalize_from_details(cls, name: str, details: dict) -> Set[str]:
        """Normalize a set of strings."""

        value = details.pop(name, None)
        if value is None:
            return set()
        elif isinstance(value, str):
            return {value}
        elif isinstance(value, set):
            return value
        else:
            return set(value)

    @classmethod
    def from_details(cls, details: dict):
        """Parse from decorator details."""

        return cls(
            passing=cls.normalize_from_details("passing", details),
            complete=cls.normalize_from_details("complete", details))

    def dump(self):
        return dict(passing=list(self.passing), complete=list(self.complete))


@dataclass(eq=False)
class Task:
    """Superclass for check, build, run."""

    name: str
    description: str

    dependencies: Dependencies
    runnable: Runnable[Result]
    details: dict

    graded: bool
    weight: Decimal
    source: str
    tags: Set[str]

    result_type: Type[Result]

    def run(self, resources: Dict[str, Any]) -> Result:
        """Do the dependency injection for the runnable."""

        dependencies = {}
        for name, parameter in inspect.signature(self.runnable).parameters.items():
            dependency = resources.get(name, parameter.default)
            if dependency == parameter.empty:
                raise ValueError(f"caught in {self.name}: could not satisfy dependency {name}")
            dependencies[name] = dependency
        result = self.runnable(**dependencies)

        if result is None:
            log.debug(f"task {self.name} did not return a result")
            return self.result_type.default()

        return result
