import abc
from typing import AnyStr, List, Sized, Union, Iterable, Collection, Callable, TypeVar, Sequence

from curricula.library.process import Interactive, TimeoutExpired, Interaction
from curricula.library.configurable import none, Configurable
from ...common import Evaluator, CompositeRunnable
from ...common.process import ProcessExecutor, ProcessStreamConnector, ProcessExitCodeConnector
from ...grader.task import Error
from . import CorrectnessResult

__all__ = (
    "as_lines",
    "lines_match",
    "lines_match_unordered",
    "CorrectnessRunnable",
    "CompareBytesEvaluator",
    "CompareExitCodeEvaluator",
    "ProcessCompareStreamTest",
    "ProcessCompareExitCodeTest",
    "write_then_read")


def as_lines(string: AnyStr) -> List[AnyStr]:
    """Strip and split by newline."""

    return string.strip().split("\n" if isinstance(string, str) else b"\n")


AnyStrSequence = Union[Iterable[AnyStr], Sized]


def lines_match(a: AnyStrSequence, b: AnyStrSequence) -> bool:
    """Check ordered equality.

    Returns a boolean indicating correctness and a list of errors
    encountered while checking.
    """

    if hasattr(a, "__len__") and hasattr(a, "__len__"):
        if len(a) != len(b):
            return False

    for x, y in zip(a, b):
        if x != y:
            return False

    return True


def lines_match_unordered(a: AnyStrSequence, b: AnyStrSequence) -> bool:
    """Check unordered equality."""

    return lines_match(sorted(a), sorted(b))


class CorrectnessRunnable(CompositeRunnable, metaclass=abc.ABCMeta):
    """Override annotation."""

    result_type = CorrectnessResult


BytesTransform = Callable[[bytes], bytes]
T = TypeVar("T")


def identity(x: T) -> T:
    return x


class CompareBytesEvaluator(Configurable, Evaluator):
    """Compares output to expected values."""

    out_transform: BytesTransform
    out_line_transform: BytesTransform
    test_out: bytes
    test_out_lines: Iterable[bytes]
    test_out_lines_lists: Iterable[Iterable[bytes]]

    def __init__(
            self,
            *,
            out_transform: BytesTransform = none,
            out_line_transform: BytesTransform = none,
            test_out: bytes = none,
            test_out_lines: Iterable[bytes] = none,
            test_out_lines_lists: Iterable[Iterable[bytes]] = none,
            **kwargs):
        """Build a test for matching stdout output.

        The list of lines from the stdout of the runtime is compared
        against each list of lines in test_out_line_lists. Note that this
        method first checks whether any error was raised during runtime.
        """

        super().__init__(**kwargs)

        self.test_out = self.resolve("test_out", local=test_out, default=None)
        self.test_out_lines = self.resolve("test_out_lines", local=test_out_lines, default=None)
        self.test_out_lines_lists = self.resolve("test_out_lines_lists", local=test_out_lines_lists, default=None)

        # Check resolvable
        resolvable = tuple(filter(None, (self.test_out, self.test_out_lines, self.test_out_lines_lists)))
        if len(resolvable) != 1:
            raise ValueError("Exactly one of test_out, test_out_lines, or test_out_lines_lists is required")

        self.out_transform = self.resolve("out_transform", local=out_transform, default=identity)
        self.out_line_transform = self.resolve("out_line_transform", local=out_line_transform, default=identity)

    def evaluate(self, out: bytes) -> CorrectnessResult:
        """Call the corresponding test."""

        if self.test_out is not None:
            return self._test_out(out)
        return self._test_out_lines_lists(out)

    def _test_out(self, out: bytes) -> CorrectnessResult:
        """Shortcut compare for one option block text."""

        test_out = self.resolve("test_out")

        out = self.out_transform(out)
        if out == test_out:
            return CorrectnessResult.shorthand()

        return CorrectnessResult.shorthand(
            passing=False,
            error=Error(description="unexpected output"),
            expected=test_out.decode(errors="replace"),
            actual=out.decode(errors="replace"))

    def _test_out_lines_lists(self, out: bytes) -> CorrectnessResult:
        """Used to compare multiple options of lists of lines."""

        if self.test_out_lines is not None:
            test_out_lines_lists = [self.test_out_lines]
        else:
            test_out_lines_lists = self.test_out_lines_lists

        out_lines = tuple(map(self.out_line_transform, self.out_transform(out).split(b"\n")))

        if any(lines_match(out_lines, lines) for lines in test_out_lines_lists):
            return CorrectnessResult.shorthand()

        expected = tuple(b"\n".join(test_out_lines).decode(errors="replace") for test_out_lines in test_out_lines_lists)
        return CorrectnessResult(
            passing=False,
            error=Error(description="unexpected output"),
            actual=b"\n".join(out_lines).decode(errors="replace"),
            expected=expected[0] if len(expected) == 1 else expected)


class CompareExitCodeEvaluator(Evaluator, Configurable):
    """Checks program exit code."""

    expected_code: int
    expected_codes: Collection[int]

    _expected_codes: Collection[int]

    def __init__(self, *, expected_code: int = none, expected_codes: Collection[int] = none, **kwargs):
        """Set expected codes."""

        super().__init__(**kwargs)

        expected_code = self.resolve("expected_code", local=expected_code, default=None)
        expected_codes = self.resolve("expected_codes", local=expected_codes, default=None)
        if expected_code is None and expected_codes is None:
            raise ValueError("Runtime exit test requires either expected status or statuses!")
        if expected_code is not None and expected_codes is not None:
            raise ValueError("Runtime exit test requires either expected status or statuses!")

        self._expected_codes = (expected_code,) if expected_code is not None else expected_codes

    def evaluate(self, code: int) -> CorrectnessResult:
        """Check if the exit code is one of the options."""

        if code in self._expected_codes:
            return CorrectnessResult(passing=True)
        return CorrectnessResult(
            passing=False,
            error=Error(
                description=f"received incorrect exit code {code}",
                suggestion=f"""expected exit code {", ".join(map(str, self._expected_codes))}"""))


class ProcessCompareStreamTest(
        ProcessExecutor,
        ProcessStreamConnector,
        CompareBytesEvaluator,
        CorrectnessRunnable):
    """Standard process output test."""


class ProcessCompareExitCodeTest(
        ProcessExecutor,
        ProcessExitCodeConnector,
        CompareExitCodeEvaluator,
        CorrectnessRunnable):
    """Make sure the process exits as expected."""


def write_then_read(
        interactive: Interactive,
        stdin: Sequence[bytes],
        read_condition: Callable[[bytes], bool] = None,
        read_condition_timeout: float = None) -> Interaction:
    """Pass in a bunch of lines, get the last output, compare."""

    if not interactive.poll():
        raise CorrectnessResult(passing=False, error=Error(description="program crashed"))

    with interactive.recording() as interaction:
        for command in stdin:
            interactive.stdin.write(command)
            try:
                interactive.stdout.read(
                    condition=read_condition,
                    timeout=read_condition_timeout)
            except TimeoutExpired:
                raise CorrectnessResult.shorthand(
                    passing=False,
                    error=Error(description="timed out"),
                    runtime=interaction.dump())

    if interaction.stdout is None:
        raise CorrectnessResult.shorthand(
            passing=False,
            error=Error(description="did not receive output"),
            runtime=interaction.dump())

    return interaction
