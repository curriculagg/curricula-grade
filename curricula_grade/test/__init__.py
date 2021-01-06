import abc
from typing import Any, Optional, Type

from ..grader.task import Result


class Executor(metaclass=abc.ABCMeta):
    """Runs the content of the test."""

    resources: dict
    details: dict

    @abc.abstractmethod
    def execute(self) -> Any:
        """Does something and produces output."""


class Connector(metaclass=abc.ABCMeta):
    """Converts the result of the executor."""

    resources: dict
    details: dict

    @abc.abstractmethod
    def connect(self, result: Any) -> Any:
        """Transforms output for evaluation."""


class Evaluator(metaclass=abc.ABCMeta):
    """Evaluates the content of a test."""

    resources: dict
    details: dict

    @abc.abstractmethod
    def evaluate(self, result: Any) -> Result:
        """Evaluate and return a result."""


class Test(metaclass=abc.ABCMeta):
    """Convenience class for building dynamic test objects."""

    resources: Optional[dict]
    details: Optional[dict]

    @property
    @abc.abstractmethod
    def result_type(self) -> Type[Result]:
        """Class-based tests must indicate a result type."""

    @abc.abstractmethod
    def execute(self) -> Any:
        """Does something and produces output."""

    def connect(self, result: Any) -> Any:
        """Transforms output for evaluation."""

        return result

    @abc.abstractmethod
    def evaluate(self, result: Any) -> Result:
        """Evaluate and return a result."""

    def __call__(self, resources: dict) -> Result:
        """Should behave like a standard runnable."""

        self.resources = resources
        self.details = dict()
        result = self.evaluate(self.connect(self.execute()))
        result.details.update(self.details)
        return result
