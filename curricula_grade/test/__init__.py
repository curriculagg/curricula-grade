import abc

from ..task import Result
from .code import CodeResult
from .complexity import ComplexityResult
from .correctness import CorrectnessResult
from .memory import MemoryResult


class Test(abc.ABC):
    """Convenience class for building dynamic test objects."""

    def __call__(self, *args, **kwargs) -> Result:
        """Should behave like a standard runnable."""
