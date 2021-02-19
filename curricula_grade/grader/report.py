from __future__ import annotations

import typing
import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

from .task import Result
from curricula.models import serialize_datetime, deserialize_datetime

if typing.TYPE_CHECKING:
    from ..models import GradingAssignment, GradingProblem


def is_some(value: Any) -> bool:
    """Shorthand for checking if identical to None."""

    return value is not None


@dataclass(eq=False)
class ProblemReportProblemReference:
    """Reference to original problem."""

    short: str
    title: str

    def dump(self) -> dict:
        return dict(short=self.short, title=self.title)

    @classmethod
    def create(cls, problem: "GradingProblem") -> "ProblemReportProblemReference":
        return ProblemReportProblemReference(short=problem.short, title=problem.title)

    @classmethod
    def load(cls, data: dict) -> "ProblemReportProblemReference":
        return ProblemReportProblemReference(**data)


@dataclass
class ProblemReportAutomated:
    """Automated results."""

    results: Dict[str, Result] = field(default_factory=dict)
    partial: bool = False

    def __getitem__(self, item: str) -> Result:
        """Look up a result by task name."""

        return self.results[item]

    def get(self, item: str) -> Optional[Result]:
        """Mimic lookup get."""

        return self.results.get(item)

    def add(self, result: Result):
        """Add a result to the report."""

        self.results[result.task.name] = result

    @classmethod
    def load(cls, data: dict, problem: GradingProblem) -> ProblemReportAutomated:
        """Load an automated report."""

        partial = data["partial"]
        results = {}
        for task in problem.grader.tasks:
            result_data = data["results"].get(task.name)
            if result_data is not None:
                results[task.name] = task.result_type.load(result_data, task)
            else:
                partial = True
        return cls(partial=partial, results=results)

    def dump(self, thin: bool = False) -> dict:
        """Dump the result to a serializable format."""

        results = {result.task.name: result.dump(thin=thin) for result in self.results.values()}
        return dict(partial=self.partial, results=results)


@dataclass(eq=False)
class ProblemReport:
    """The final report returned by the testing framework."""

    problem: ProblemReportProblemReference
    automated: ProblemReportAutomated

    @classmethod
    def create(cls, problem: GradingProblem) -> "ProblemReport":
        """Create a new problem."""

        return ProblemReport(
            problem=ProblemReportProblemReference.create(problem),
            automated=ProblemReportAutomated())

    @classmethod
    def load(cls, data: dict, problem: GradingProblem) -> "ProblemReport":
        """Deserialize, rebinding to provided tasks."""

        return ProblemReport(
            problem=ProblemReportProblemReference.load(data["problem"]),
            automated=ProblemReportAutomated.load(a, problem) if is_some(a := data["automated"]) else None)

    def dump(self, thin: bool = False) -> dict:
        """Serialize."""

        return dict(
            problem=self.problem.dump(),
            automated=self.automated.dump(thin=thin))


@dataclass(eq=False)
class AssignmentReportAssignmentReference:
    """Structured data about the origin assignment."""

    short: str
    title: str
    # hash: str

    def dump(self) -> dict:
        return dict(short=self.short, title=self.title)

    @classmethod
    def create(cls, assignment: GradingAssignment) -> "AssignmentReportAssignmentReference":
        return AssignmentReportAssignmentReference(short=assignment.short, title=assignment.title)

    @classmethod
    def load(cls, data: dict):
        return AssignmentReportAssignmentReference(**data)


@dataclass(eq=False)
class AssignmentReport:
    """Aggregation of problem reports."""

    assignment: AssignmentReportAssignmentReference
    problems: Dict[str, ProblemReport] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def __contains__(self, item: str) -> bool:
        return item in self.problems

    def __getitem__(self, item: str) -> ProblemReport:
        """Index problem reports by problem short."""

        return self.problems[item]

    def __setitem__(self, key: str, value: ProblemReport):
        """Set the result from a problem."""

        self.problems[key] = value

    def dump(self, thin: bool = False) -> dict:
        """Serialize as dictionary to shorten rebuild."""

        return dict(
            assignment=self.assignment.dump(),
            timestamp=serialize_datetime(self.timestamp),
            problems={short: report.dump(thin=thin) for short, report in self.problems.items()})

    def partial(self) -> bool:
        return any(problem.automated.partial for problem in self.problems.values())

    @classmethod
    def create(cls, assigment: "GradingAssignment") -> "AssignmentReport":
        """Create from assignment for metadata."""

        return AssignmentReport(assignment=AssignmentReportAssignmentReference.create(assigment))

    @classmethod
    def load(cls, data: dict, assignment: "GradingAssignment") -> "AssignmentReport":
        """Deserialize and bind to existing tasks."""

        assignment_reference = AssignmentReportAssignmentReference.load(data.pop("assignment"))
        timestamp = deserialize_datetime(data.pop("timestamp"))

        problems = {}
        for problem in assignment.problems:
            if problem.grading.is_automated:
                problems[problem.short] = ProblemReport.load(data["problems"][problem.short], problem)

        return AssignmentReport(
            assignment=assignment_reference,
            problems=problems,
            timestamp=timestamp)
