import argparse
import random
import json
from pathlib import Path
from typing import TextIO, Iterable, Optional

from curricula.shell.plugin import Plugin, PluginDispatcher, PluginException
from curricula.library.serialization import dump
from curricula.log import log

from .run import run, run_batch
from .models import GradingAssignment
from .grader.report import AssignmentReport


def make_report_name(target_path: Path, extension: str) -> str:
    """Generate a report file name."""

    return f"{target_path.parts[-1]}.report.{extension}"


def change_extension(report_path: Path, extension: str) -> str:
    """Return the report name with a different extension."""

    basename = report_path.parts[-1].rsplit(".", maxsplit=1)[0]
    return f"{basename}.{extension}"


def dump_report(report: AssignmentReport, file: TextIO, thin: bool = False):
    """Write a dict of reports to a file."""

    dump(report.dump(thin=thin), file, indent=2)


def amend_report(
        assignment: GradingAssignment,
        existing_report_path: Path,
        new_report: AssignmentReport) -> AssignmentReport:
    """Amend an existing report and return the merged result."""

    with existing_report_path.open() as file:
        existing_report = AssignmentReport.load(json.load(file), assignment)
    for problem_short, problem_report in new_report.problems.items():
        for task_name, result in problem_report.automated.results.items():
            existing_report[problem_short].automated.results[task_name] = result
    return existing_report


def path_from_options(
        options: dict,
        default_file_name: str,
        *,
        batch: bool,
        required: bool = True) -> Optional[Path]:
    """Return an open file and whether to close it after."""

    if options["file"] is not None:
        if batch:
            raise PluginException("Cannot use --file for batch grading, use --directory")
        output_path = Path(options["file"])
        if not output_path.parent.exists():
            raise PluginException(f"Containing directory {output_path.parent} does not exist")
        return output_path
    elif options["directory"] is not None:
        return Path(options["directory"]).joinpath(default_file_name)
    elif required:
        raise PluginException("Output file or directory must be specified!")

    return None


class GradeRunPlugin(Plugin):
    """For running submissions."""

    name = "run"
    help = "run submissions against a grading artifact"

    def setup(self, parser: argparse.ArgumentParser):
        """Command line."""

        parser.add_argument("--grading", "-g", required=True, help="the grading artifact")
        parser.add_argument("--skip", action="store_true", help="skip reports that have already been run")
        parser.add_argument("--report", "-r", action="store_true", help="whether to log test results")
        parser.add_argument("--concise", "-c", action="store_true", help="whether to report concisely")
        parser.add_argument("--progress", "-p", action="store_true", help="show progress in batch")
        parser.add_argument("--sample", type=int, help="randomly sample batch")
        parser.add_argument("--tags", nargs="+", help="only run tasks with the specified tags")
        parser.add_argument("--tasks", nargs="+", help="only run the specified tasks")
        parser.add_argument("--summarize", action="store_true", help="summarize after running batch")
        parser.add_argument("--thin", action="store_true", help="shorten output for space")
        parser.add_argument("--amend", action="store_true", help="amend any existing report at the destination")
        to_group = parser.add_mutually_exclusive_group(required=True)
        to_group.add_argument("-f", "--file", dest="file", help="output file for single report")
        to_group.add_argument("-d", "--directory", dest="directory", help="where to write reports to if batched")
        parser.add_argument("submissions", nargs="+", help="run tests on a single target")

    def main(self, parser: argparse.ArgumentParser, arguments: dict) -> int:
        """Run the grader."""

        grading_path: Path = Path(arguments["grading"]).absolute()
        if not grading_path.is_dir():
            raise PluginException("grading artifact does not exist!")

        if len(arguments["submissions"]) == 1:
            submission_path = Path(arguments["submissions"][0]).absolute()
            return self.run_single(grading_path, submission_path, arguments)
        else:
            return self.run_batch(grading_path, map(Path, arguments.get("submissions")), arguments)

    @classmethod
    def run_single(cls, grading_path: Path, assignment_path: Path, options: dict) -> int:
        """Grade a single file, write to file output."""

        log.debug(f"running single target {assignment_path}")
        assignment = GradingAssignment.read(grading_path)

        report = run(assignment, assignment_path, options=options)
        report_path = path_from_options(options, make_report_name(assignment_path, "json"), batch=False)
        if options["amend"] and report_path.is_file():
            report = amend_report(assignment, report_path, report)

        with report_path.open("w") as file:
            dump_report(report, file, thin=options.get("thin"))

        return 0

    @classmethod
    def run_batch(cls, grading_path: Path, target_paths: Iterable[Path], options: dict) -> int:
        """Run a batch of reports."""

        log.debug("running batch submissions")

        assignment = GradingAssignment.read(grading_path)

        # Check which reports have already been run if flagged
        if options["skip"]:
            log.debug("determining reports to skip")
            new_target_paths = []
            skip_count = 0
            for target_path in target_paths:
                report_path = path_from_options(options, make_report_name(target_path, "json"), batch=True)
                if not report_path.parent.exists():
                    log.info(f"making report directory {report_path.parent}")
                    report_path.parent.mkdir(parents=True)
                if not report_path.exists():
                    new_target_paths.append(target_path)
                else:
                    skip_count += 1
            log.info(f"found {skip_count} reports to skip")
            target_paths = new_target_paths

        target_paths = tuple(target_paths)

        # Do random sampling
        sample = options.get("sample")
        if sample is not None:
            target_paths = random.sample(target_paths, sample)

        report_paths = []
        for i, (target_path, report) in enumerate(run_batch(assignment, target_paths, options=options)):
            report_path = path_from_options(options, make_report_name(target_path, "json"), batch=True)
            if options["amend"] and report_path.is_file():
                report = amend_report(assignment, report_path, report)

            with report_path.open("w") as file:
                dump_report(report, file)
            report_paths.append(report_path)

            # Print progress
            if options.get("progress"):
                print(f"{i + 1}/{len(target_paths)} graded")

        if options.get("summarize"):
            from curricula_grade.tools.summarize import summarize
            summarize(grading_path, report_paths)

        return 0


class GradeSummarizePlugin(Plugin):
    """Summarize the results of a set of reports."""

    name = "summarize"
    help = "summarize the results of a set of reports"

    def setup(self, parser: argparse.ArgumentParser):
        """No options."""

        parser.add_argument("--grading", "-g", required=True, help="the grading artifact")
        parser.add_argument("reports", nargs="+", help="the reports to summarize")

    def main(self, parser: argparse.ArgumentParser, arguments: dict):
        """Summarize a batch of reports."""

        grading_path: Path = Path(arguments["grading"]).absolute()
        if not grading_path.is_dir():
            raise PluginException("grading artifact does not exist!")

        from .tools.summarize import summarize
        summarize(grading_path, list(map(Path, arguments["reports"])))


class GradeDiagnosePlugin(Plugin):
    """Get formatted diagnostics on a single report."""

    name = "diagnose"
    help = "get formatted diagnostics on a single report"

    def setup(self, parser: argparse.ArgumentParser):
        """No arguments."""

        parser.add_argument("report", help="report to print diagnostics on")

    def main(self, parser: argparse.ArgumentParser, arguments: dict):
        """Get diagnostics on a report."""

        grading_path: Path = Path(arguments["grading"]).absolute()
        if not grading_path.is_dir():
            raise PluginException("grading artifact does not exist!")

        assignment = GradingAssignment.read(grading_path)
        report_path = Path(arguments["report"])

        from curricula_grade.tools.diagnostics import get_diagnostics
        print(get_diagnostics(assignment, report_path), end="")


class GradePlugin(PluginDispatcher):
    """Implement grade plugin."""

    name = "grade"
    help = "manage assignment grading for submissions"
    plugins = (
        GradeRunPlugin(),
        GradeSummarizePlugin(),
        GradeDiagnosePlugin())

    @classmethod
    def compare(cls, grading_path: Path, options: dict):
        """Generate a comparison of two files."""

        from curricula_grade.tools.compare import compare_output

        report_path = Path(options.get("report"))
        template_path = Path(options.get("template"))
        with path_from_options(options, change_extension(report_path, "compare.html"), batch=False).open("w") as file:
            file.write(compare_output(template_path, report_path))
