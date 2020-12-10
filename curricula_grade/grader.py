from typing import Callable
from dataclasses import dataclass, field

from curricula.log import log

from .report import ProblemReport
from .resource import Context, Submission
from .exception import GraderException
from .task import Task, Result
from .task.dependency import fulfills_dependencies
from .task.registrar import TaskRegistrar
from .task.filter import TaskFilter
from .task.collection import TaskCollection


import typing

if typing.TYPE_CHECKING:
    from .models import GradingProblem


def _run(
        tasks: TaskCollection,
        is_visible: Callable[[Task], bool],
        resources: dict,
        report: ProblemReport):
    """Execute sorted tasks, skipping if missing dependencies."""

    log.debug("running tasks")
    for task in tasks:
        log.debug(f"running task {task.name}")

        # Check conditions for whether this case is filtered out, if so report is partial
        if not is_visible(task):
            report.partial = True
            continue

        # If we can't run it, mark as incomplete
        elif not fulfills_dependencies(task, report):
            result = task.result_type.incomplete()

        # Run task if not hidden and dependencies are met
        else:
            try:
                result = task.run(resources)

            # Results may be raised
            except Result as r:
                result = r

            # Check if the result is the right type
            if type(result) is not task.result_type:
                raise GraderException(f"expected result type {task.result_type.kind} from {task.name} in {task.source}")

        result.task = task
        report.add(result)


@dataclass(eq=False)
class Grader:
    """A main class for grading runtime."""

    tasks: TaskCollection

    # Populated on import
    problem: "GradingProblem" = field(init=False)

    # Task registration
    register: TaskRegistrar

    def __post_init__(self):
        self.register = TaskRegistrar(tasks=self.tasks)

    def run(self, context: Context, submission: Submission) -> ProblemReport:
        """Build and test."""

        log.debug("setting up runtime")

        # Resources
        resources = dict(context=context, submission=submission, problem=self.problem)
        resources.update(resources=resources)

        # Create the filter
        is_visible = TaskFilter(self.tasks, context, self.problem.short)

        # Final report
        report = ProblemReport.create(self.problem)

        # Run each stage
        _run(self.tasks, is_visible, resources, report)

        return report
