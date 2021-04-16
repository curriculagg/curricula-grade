from curricula.library.configurable import Configurable
from curricula.library.valgrind import ValgrindReport, run
from ...common.process import ProcessExecutor
from ...common import Evaluator, CompositeRunnable
from . import MemoryResult

import abc


class ValgrindProcessExecutor(ProcessExecutor):
    """Runs valgrind on the executable with given parameters."""

    def execute(self) -> ValgrindReport:
        executable = self.resources[self.executable_name]
        report = run(
            *executable.args,
            *self.args,
            stdin=self.stdin,
            timeout=self.timeout,
            cwd=self.cwd)
        self.details["report"] = report.dump()
        return report


class ValgrindEvaluator(Evaluator, Configurable):
    """Wrap the report as a result.s"""

    def evaluate(self, report: ValgrindReport) -> MemoryResult:
        return MemoryResult.from_valgrind_report(report)


class MemoryRunnable(CompositeRunnable, metaclass=abc.ABCMeta):
    """Override annotation."""

    result_type = MemoryResult


class MemoryTest(ValgrindProcessExecutor, ValgrindEvaluator, MemoryRunnable):
    """Standard Valgrind memory test."""
