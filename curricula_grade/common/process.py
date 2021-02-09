from typing import Iterable, Optional, Any, Type
from pathlib import Path

from curricula.library.configurable import Configurable, none
from curricula.library.process import Runtime
from ..grader.task import Error, Result
from . import Executor, Connector


class ProcessExecutor(Configurable, Executor):
    """Meant for reading and comparing stdout."""

    executable_name: str
    args: Iterable[str]
    stdin: Optional[bytes]
    timeout: Optional[float]
    cwd: Optional[Path]
    stream: str

    def __init__(
            self,
            *,
            executable_name: str = none,
            args: Iterable[str] = none,
            stdin: bytes = none,
            timeout: float = none,
            cwd: Path = none,
            stream: str = none,
            **kwargs):
        """Save container information, call super."""

        super().__init__(**kwargs)

        self.executable_name = executable_name
        self.args = args
        self.stdin = stdin
        self.timeout = timeout
        self.cwd = cwd
        self.stream = stream

    def execute(self) -> Runtime:
        """Check that it ran correctly, then run the test."""

        executable = self.resources[self.executable_name]
        runtime = executable.execute(
            *self.resolve("args", default=()),
            stdin=self.resolve("stdin", default=None),
            timeout=self.resolve("timeout", default=None),
            cwd=self.resolve("cwd", default=None))
        self.details["runtime"] = runtime.dump()
        return runtime


class ProcessInputFileMixin(Configurable):
    """Enables the use of an input file rather than stdin string."""

    input_file_path: Path

    def __init__(self, *, input_file_path: Path = none, **kwargs):
        """Set stdin to the contents of the file."""

        super().__init__(**kwargs)
        self.input_file_path = input_file_path


class ProcessExitCodeConnector(Connector):
    """Output is exit code instead of stdout."""

    def connect(self, runtime: Runtime) -> int:
        """Return exit code."""

        self.details.update(runtime=runtime.dump())
        return runtime.code


class ProcessStreamConnector(Configurable, Connector):
    """Output is stdout or stderr."""

    STDOUT = "stdout"
    STDERR = "stderr"

    stream: str

    def connect(self, runtime: Runtime) -> bytes:
        """Return exit code."""

        self.details.update(runtime=runtime.dump())
        stream = self.resolve("stream", default=self.STDOUT)
        if stream == self.STDOUT:
            return runtime.stdout
        elif stream == self.STDERR:
            return runtime.stderr
        raise ValueError(f"invalid stream type specified in connector: {stream}")


class OutputFileConnector(Configurable, Connector):
    """Enables the use of an input file rather than stdin string."""

    output_file_path: Path

    def __init__(self, *, output_file_path: Path = none, **kwargs):
        """Set stdin."""

        super().__init__(**kwargs)
        self.output_file_path = output_file_path

    def connect(self, result: Any) -> bytes:
        """Call super because it might do something."""

        output_file_path = self.resolve("output_file_path")
        if not output_file_path.is_file():
            raise self.result_type(
                complete=True,
                passing=False,
                error=Error(description="no output file", suggestion=f"expected path {output_file_path}"))
        return output_file_path.read_bytes()


def verify_runtime(runtime: Runtime, result_type: Type[Result]) -> Runtime:
    """Basic checks on runtime post conditions."""

    if runtime.raised_exception:
        error = Error(description=runtime.exception.description)
        raise result_type(complete=True, passing=False, error=error, details=dict(runtime=runtime.dump()))
    if runtime.timed_out:
        error = Error(
            description="timed out",
            suggestion=f"exceeded maximum elapsed time of {runtime.timeout} seconds")
        raise result_type(complete=True, passing=False, error=error, details=dict(runtime=runtime.dump()))
    if runtime.code != 0:
        error = Error(
            description=f"received status code {runtime.code}",
            suggestion="expected status code of zero")
        raise result_type(complete=True, passing=False, error=error, details=dict(runtime=runtime.dump()))
    return runtime


class VerifyRuntimeConnector(Connector):
    """Determine whether a runtime succeeded."""

    def connect(self, runtime: Runtime) -> Runtime:
        """See if the runtime raised exceptions or returned status code."""

        return verify_runtime(runtime, self.result_type)
