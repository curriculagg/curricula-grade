from decimal import Decimal
from typing import Optional, Union, List

from curricula.library.valgrind import ValgrindReport

from ...grader.task import Result, Error, Message


class MemoryResult(Result):
    """Result of a memory leak test."""

    kind = "memory"

    error_count: Optional[int]
    leaked_blocks: Optional[int]
    leaked_bytes: Optional[int]

    def __init__(
            self,
            passing: bool,
            complete: bool = True,
            error_count: int = None,
            leaked_blocks: int = None,
            leaked_bytes: int = None,
            score: Union[Decimal, int, float, str] = None,
            error: Error = None,
            messages: List[Message] = None,
            details: dict = None):
        """Initialize a memory result."""

        super().__init__(
            complete=complete,
            passing=passing,
            details=details,
            score=score,
            error=error,
            messages=messages)

        self.error_count = error_count
        self.leaked_blocks = leaked_blocks
        self.leaked_bytes = leaked_bytes

        if self.error is None:
            if error_count is not None and error_count > 0 or leaked_bytes is not None and leaked_bytes > 0:
                self.error = Error(description=f"leaked {leaked_bytes} bytes with {error_count} errors")

    @classmethod
    def from_valgrind_report(cls, report: ValgrindReport, **details) -> "MemoryResult":
        """Generate a memory test result from a valgrind report."""

        if report is None:
            return MemoryResult(passing=False, complete=False, details=details)

        if report.exception is not None:
            return cls(
                complete=False,
                passing=False,
                error=Error(report.exception),
                details=details)

        leaked_blocks, leaked_bytes = report.memory_lost()
        return cls(
            passing=leaked_bytes == 0 and len(report.errors) == 0,
            error_count=len(report.errors),
            leaked_blocks=leaked_blocks,
            leaked_bytes=leaked_bytes,
            details=details)

    def dump(self, thin: bool = False) -> dict:
        dump = super().dump(thin=thin)
        dump.update(
            error_count=self.error_count,
            leaked_blocks=self.leaked_blocks,
            leaked_bytes=self.leaked_bytes)
        return dump
