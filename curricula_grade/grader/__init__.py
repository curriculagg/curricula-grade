from curricula.log import log

from .task import Result
from .report import ProblemReport
from .task.dependency import fulfills_dependencies
from .task.registrar import TaskRegistrar
from .task.filter import filter_tasks
from .task.collection import TaskCollection
from ..resource import Context, Submission
from ..exception import GraderException

import typing

if typing.TYPE_CHECKING:
    from ..models import GradingProblem

__all__ = ("Grader",)


class Grader:
    """A main class for grading runtime."""

    register: TaskRegistrar

    # Assigned on import
    problem: "GradingProblem"

    def __init__(self):
        """Create the registrar."""

        self.register = TaskRegistrar()

    @property
    def tasks(self) -> TaskCollection:
        """Mirror register tasks."""

        return self.register.tasks

    def run(self, context: Context, submission: Submission) -> ProblemReport:
        """Build and test."""

        log.debug("setting up runtime")

        # Resources
        resources = dict(context=context, submission=submission, problem=self.problem)
        resources.update(resources=resources)

        # Create the filter
        filtered_task_names = filter_tasks(
            context=context,
            problem_short=self.problem.short,
            tasks=self.register.tasks)

        # Report
        report = ProblemReport.create(self.problem)

        # Execute
        for task in self.tasks:
            log.debug(f"running task {task.name}")

            # Check conditions for whether this case is filtered out, if so report is partial
            if task.name not in filtered_task_names:
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
                        f"expected result type {task.result_type} from {task.name} in {task.source}")

            result.task = task
            report.automated.add(result)

        return report
