import abc
from typing import Any, Optional, Type

from ..grader.task import Result

__all__ = (
    "Executor",
    "Connector",
    "Evaluator",
    "Runnable",
    "CompositeRunnable",)


class Runnable(metaclass=abc.ABCMeta):
    """Convenience class for building dynamic test objects."""

    @property
    @abc.abstractmethod
    def result_type(self) -> Type[Result]:
        """Class-based tests must indicate a result type."""

    @abc.abstractmethod
    def __call__(self, **kwargs) -> Type[Result]:
        """Must implement runnable invocation."""


class Executor(metaclass=abc.ABCMeta):
    """Runs the content of the test."""

    result_type: Type[Result]
    resources: dict
    details: dict

    @abc.abstractmethod
    def execute(self) -> Any:
        """Does something and produces output."""


class Connector(metaclass=abc.ABCMeta):
    """Converts the result of the executor."""

    result_type: Type[Result]
    resources: dict
    details: dict

    @abc.abstractmethod
    def connect(self, result: Any) -> Any:
        """Transforms output for evaluation."""


class Evaluator(metaclass=abc.ABCMeta):
    """Evaluates the content of a test."""

    result_type: Type[Result]
    resources: dict
    details: dict

    @abc.abstractmethod
    def evaluate(self, result: Any) -> Result:
        """Evaluate and return a result."""


class CompositeRunnable(Runnable, metaclass=abc.ABCMeta):
    """Separate responsibilities."""

    resources: Optional[dict]
    details: Optional[dict]

    @abc.abstractmethod
    def execute(self) -> Any:
        """Does something and produces output."""

    @abc.abstractmethod
    def evaluate(self, result: Any) -> Result:
        """Evaluate and return a result."""

    def __call__(self, resources: dict) -> Result:
        """Should behave like a standard runnable."""

        self.resources = resources
        self.details = dict()

        intermediate = self.execute()
        if (connect := getattr(self, "connect", None)) is not None:
            intermediate = connect(intermediate)
        result = self.evaluate(intermediate)
        result.details.update(self.details)
        return result
