import json
from pathlib import Path

from curricula.library.printer import Printer
from ..models import GradingAssignment
from ..grader.report import AssignmentReport


def diagnose(assignment: GradingAssignment, assignment_report_path: Path) -> str:
    """Check if tests passed, displaying errors."""

    # Load the assignment
    with assignment_report_path.open() as file:
        assignment_report = AssignmentReport.load(json.load(file), assignment)

    # Create buffer
    output = Printer()

    # Iterate problems
    for problem in assignment.problems:
        if problem.short not in assignment_report:
            continue

        problem_report = assignment_report[problem.short]
        results = list(problem_report.automated.results.values())
        results_count = len(results)
        results_passing_count = sum(1 for _ in filter(lambda p: p.passing, results))

        # Problem summary header
        output.print(f"Problem {problem.short}: {results_passing_count}/{results_count}")

        # Iterate results
        output.indent()
        for task in problem.grader.tasks:
            result = problem_report.automated.get(task.name)
            if result is None:
                continue

            if not result.complete:
                output.print(f"✗ {task.name} did not complete")
            elif not result.passing:
                output.print(f"✗ {task.name} failed")
                output.indent()
                if result.error:
                    if result.error.location:
                        output.print(f"Reason: {result.error.description}")
                        output.print(f"Location: {result.error.location}")
                    if result.error.traceback:
                        output.print("Traceback: ")
                        output.print(result.error.traceback.strip(), indentation=2)
                    # if result.error.expected:
                    #     output.print(f"Expected: {repr(result.error.expected)}")
                    # if result.error.received:
                    #     output.print(f"Received: {repr(result.error.received)}")
                output.dedent()
            else:
                output.print(f"✓ {task.name} passed")

        output.dedent()
    return str(output)
