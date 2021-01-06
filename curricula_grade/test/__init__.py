import abc
from typing import Any, Union, Optional

from ..grader.task import Result
from .code import CodeResult
from .complexity import ComplexityResult
from .correctness import CorrectnessResult
from .memory import MemoryResult


class Executor(abc.ABC):
    """Runs the content of the test."""

    resources: dict
    details: dict

    @abc.abstractmethod
    def execute(self) -> Any:
        """Does something and produces output."""


class Connector(abc.ABC):
    """Converts the result of the executor."""

    resources: dict
    details: dict

    @abc.abstractmethod
    def connect(self, result: Any) -> Any:
        """Transforms output for evaluation."""


class Evaluator(abc.ABC):
    """Evaluates the content of a test."""

    resources: dict
    details: dict

    @abc.abstractmethod
    def evaluate(self, result: Any) -> Result:
        """Evaluate and return a result."""


class Test(Executor, Connector, Evaluator, abc.ABC):
    """Convenience class for building dynamic test objects."""

    _resources: Optional[dict]
    _details: Optional[dict]

    @property
    def resources(self) -> dict:
        return self._resources

    @property
    def details(self) -> dict:
        return self._details

    def connect(self, result: Any) -> Any:
        return result

    def __call__(self, resources: dict) -> Result:
        """Should behave like a standard runnable."""

        self._resources = resources
        self._details = dict()
        result = self.evaluate(self.connect(self.execute()))
        result.details.update(self._details)
        return result
