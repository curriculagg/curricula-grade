import abc
from typing import Dict, TypeVar, Callable, Any, Type, Set, Optional, List, Union
from dataclasses import dataclass, field
from decimal import Decimal

from curricula.library.inject import inject
from curricula.log import log

__all__ = ("Message", "Result", "Dependencies", "Task", "Runnable", "Error")


@dataclass
class Message:
    """A message associated with a result."""

    class Kind:
        WARNING = "warning"
        INFO = "info"
        DEBUG = "debug"

    kind: str
    content: str

    def dump(self) -> dict:
        return dict(kind=self.kind, content=self.content)

    @classmethod
    def load(cls, data: dict) -> "Message":
        return cls(kind=data["kind"], content=data["content"])


@dataclass
class Error:
    """An error raised during a task."""

    description: str
    suggestion: str = None
    location: str = None
    traceback: str = None

    def dump(self, thin: bool = False) -> dict:
        if thin:
            return dict(description=self.description, suggestion=self.suggestion)
        return dict(
            description=self.description,
            suggestion=self.suggestion,
            location=self.location,
            traceback=self.traceback)

    @classmethod
    def load(cls, data: dict) -> "Error":
        return cls(**data)


@dataclass(init=False)
class Result(Exception, abc.ABC):
    """The result of a test."""

    complete: bool
    passing: bool
    details: dict
    error: Error
    messages: Optional[List[Message]]
    score: Decimal

    task: "Task" = field(init=False, repr=False)

    def __init__(
            self,
            passing: bool,
            complete: bool = True,
            score: Union[Decimal, int, float, str] = None,
            error: Error = None,
            messages: List[Message] = None,
            details: dict = None):
        """Initialize a new result.

        Details are passed as a dictionary in order to avoid potential
        collisions with normal arguments.
        """

        self.complete = complete
        self.passing = passing
        self.score = score
        self.error = error
        self.messages = messages if messages is not None else list()
        self.details = details if details is not None else dict()

    def dump(self, thin: bool = False) -> dict:
        """Serialize the result for JSON."""

        dump = dict(
            complete=self.complete,
            passing=self.passing,
            score=str(self.score) if self.score is not None else None,
            error=self.error.dump(thin=thin) if self.error is not None else None,
            messages=[message.dump() for message in self.messages],
            task=dict(name=self.task.name, description=self.task.description))
        if not thin:
            dump.update(details=self.details)
        return dump

    @classmethod
    def load(cls, data: dict, task: "Task") -> "Result":
        """Load a result from serialized."""

        data.pop("task")
        score = Decimal(score_data) if (score_data := data.pop("score", None)) is not None else None
        error = Error.load(error_data) if (error_data := data.pop("error", None)) is not None else None
        messages = list(map(Message.load, data.pop("messages")))
        self = cls(**data, score=score, error=error, messages=messages)
        self.task = task
        return self

    @classmethod
    def incomplete(cls):
        """Return a mock result if the task was not completed."""

        return cls(complete=False, passing=False)

    @classmethod
    def default(cls):
        """Called in special cases if no result is returned."""

        return cls(complete=True, passing=True)

    @classmethod
    def shorthand(cls, passing: bool = True, complete: bool = True, error: Error = None, **details):
        """Expand details."""

        cls(complete=complete, passing=passing, error=error, details=details)


TResult = TypeVar("TResult", bound=Result)
Runnable = Callable[[], TResult]


@dataclass
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


@dataclass(eq=False)
class Task:
    """Superclass for check, build, run."""

    name: str
    description: str

    dependencies: Dependencies
    runnable: Runnable[Result]
    details: dict

    graded: bool
    weight: Optional[Decimal]
    points: Optional[Decimal]

    source: str
    tags: Set[str]

    result_type: Type[Result]

    def run(self, resources: Dict[str, Any]) -> Result:
        """Do the dependency injection for the runnable."""

        try:
            result = inject(resources, self.runnable)
        except ValueError as error:
            raise ValueError(f"caught in {self.name}: {error}")

        if result is None:
            log.debug(f"task {self.name} did not return a result")
            return self.result_type.default()

        return result
