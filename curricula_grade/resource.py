from typing import Dict, Tuple, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass, field

from curricula.library import process
from curricula.library import callgrind

__all__ = ("Resource", "Submission", "Context", "File", "Executable", "ExecutableFile")


class Resource:
    """A resource required for a test."""


@dataclass(eq=False)
class Submission(Resource):
    """The execution context of the tests."""

    problem_path: Path
    assignment_path: Path


@dataclass(eq=False)
class Context(Resource):
    """Extra context."""

    options: Dict[str, Any] = field(default_factory=dict)
    task_names: Optional[Set[str]] = None
    task_tags: Optional[Set[str]] = None

    @classmethod
    def from_options(cls, options: Dict[str, Any]) -> "Context":
        """Parse a couple of the predefined options out of the dictionary."""

        self = cls(options)
        if (tasks := options.pop("tasks", None)) is not None:
            self.task_names = set(tasks)
        if (tags := options.pop("tags", None)) is not None:
            self.task_tags = set(tags)
        return self


@dataclass(eq=False)
class File(Resource):
    """A resource corresponding to a file."""

    path: Path


@dataclass(eq=False)
class Executable(Resource):
    """A runnable testing target program."""

    args: Tuple[str, ...]

    def __init__(self, *args: str):
        self.args = args

    def interactive(self, *args: str, cwd: Path = None) -> process.Interactive:
        """Return a subprocess."""

        return process.Interactive(args=self.args + args, cwd=cwd)

    def execute(self, *args: str, stdin: bytes = None, timeout: float = None, cwd: Path = None) -> process.Runtime:
        """Run the target with command line arguments."""

        return process.run(*self.args, *args, stdin=stdin, timeout=timeout, cwd=cwd)

    def count(
            self,
            *args: str,
            stdin: bytes = None,
            timeout: float = None,
            function_name: str = None,
            cwd: Path = None) -> Tuple[process.Runtime, int]:
        """Count the instructions executed during runtime."""

        return callgrind.count(
            *self.args,
            *args,
            stdin=stdin,
            timeout=timeout,
            function_name=function_name,
            cwd=cwd)


@dataclass(eq=False)
class ExecutableFile(Executable, File):
    """A local file that can be executed."""

    def __init__(self, path: Path, *args: str):
        super().__init__()
        self.path = path
        self.args = (str(path),) + args
