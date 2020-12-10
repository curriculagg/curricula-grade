from dataclasses import dataclass, field

from curricula.log import log

from ..grader.report import ProblemReport
from ..resource import Context, Submission
from ..exception import GraderException

from .task import Result
from .task.dependency import fulfills_dependencies
from .task.registrar import TaskRegistrar
from .task.filter import TaskFilter
from .task.collection import TaskCollection


import typing

if typing.TYPE_CHECKING:
    from ..models import GradingProblem


@dataclass(eq=False)
class Grader:
    """A main class for grading runtime."""

    tasks: TaskCollection

    # Populated on import
    problem: "GradingProblem" = field(init=False)

    # Task registration
    register: TaskRegistrar

    def __post_init__(self):
        """Set task registration."""

        self.register = TaskRegistrar(tasks=self.tasks)

    def run(self, context: Context, submission: Submission) -> ProblemReport:
        """Build and test."""

        log.debug("setting up runtime")

        # Resources
        resources = dict(context=context, submission=submission, problem=self.problem)
        resources.update(resources=resources)

        # Create the filter
        task_filter = TaskFilter(self.tasks, context, self.problem.short)

        # Report
        report = ProblemReport.create(self.problem)

        # Execute
        for task in self.tasks:
            log.debug(f"running task {task.name}")

            # Check conditions for whether this case is filtered out, if so report is partial
            if not task_filter(task):
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
                    raise GraderException(
                        f"expected result type {task.result_type.kind} from {task.name} in {task.source}")

            result.task = task
            report.add(result)

        return report
