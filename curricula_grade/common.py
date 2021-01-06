from typing import TypeVar, Type

from curricula.library.process import Runtime
from .grader.task import Error, Result


TResult = TypeVar("TResult", bound=Type[Result])


def verify_runtime(runtime: Runtime, result_type: TResult):
    """See if the runtime raised exceptions or returned status code."""

    if runtime.raised_exception:
        error = Error(description=runtime.exception.description)
        raise result_type(passing=False, runtime=runtime.dump(), error=error)
    if runtime.timed_out:
        error = Error(
            description="timed out",
            suggestion=f"exceeded maximum elapsed time of {runtime.timeout} seconds")
        raise result_type(passing=False, runtime=runtime.dump(), error=error)
    if runtime.code != 0:
        error = Error(
            description=f"received status code {runtime.code}",
            suggestion="expected status code of zero")
        raise result_type(passing=False, runtime=runtime.dump(), error=error)
