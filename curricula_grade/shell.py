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
        options: argparse.Namespace,
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

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser):
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
        parser.add_argument("targets", nargs="+", help="run tests on a single target")

    @classmethod
    def main(cls, parser: argparse.ArgumentParser, arguments: argparse.Namespace) -> int:
        """Run the grader."""

        grading_path: Path = Path(arguments["grading"]).absolute()
        if not grading_path.is_dir():
            raise PluginException("Grading artifact does not exist!")

        if len(arguments["targets"]) == 1:
            assigment_path = Path(arguments["targets"][0]).absolute()
            return cls.run_single(grading_path, assigment_path, arguments)
        else:
            return cls.run_batch(grading_path, map(Path, arguments.get("targets")), arguments)

    @classmethod
    def run_single(cls, grading_path: Path, assignment_path: Path, options: argparse.Namespace) -> int:
        """Grade a single file, write to file output."""

        log.debug(f"running single target {assignment_path}")
        assignment = GradingAssignment.read(grading_path)

        report = run(assignment, assignment_path, options=vars(options))
        report_path = path_from_options(options, make_report_name(assignment_path, "json"), batch=False)
        if options["amend"] and report_path.is_file():
            report = amend_report(assignment, report_path, report)

        with report_path.open("w") as file:
            dump_report(report, file, thin=options.get("thin"))

        return 0

    @classmethod
    def run_batch(cls, grading_path: Path, target_paths: Iterable[Path], options: argparse.Namespace) -> int:
        """Run a batch of reports."""

        log.debug("running batch targets")

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
        for i, (target_path, report) in enumerate(run_batch(assignment, target_paths, options=vars(options))):
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


class GradePlugin(PluginDispatcher):
    """Implement grade plugin."""

    name = "grade"
    help = "manage assignment grading for submissions"
    plugins = (GradeRunPlugin,)

    @classmethod
    def _setup(cls, parser: argparse.ArgumentParser):
        """Setup argument parser for grade command."""

        subparsers = parser.add_subparsers(required=True, dest="command")

        summarize_parser = subparsers.add_parser("summarize")
        summarize_parser.add_argument("reports", help="the directory containing the grade reports")

        compare_parser = subparsers.add_parser("compare")
        to_group = compare_parser.add_mutually_exclusive_group(required=True)
        to_group.add_argument("-f", "--file", dest="file", help="output file for single report")
        to_group.add_argument("-d", "--directory", dest="directory", help="where to write reports to if batched")
        compare_parser.add_argument("-t", "--template", help="the template folder to pull from", required=True)
        compare_parser.add_argument("report", help="the report to compare")

        diagnostics_parser = subparsers.add_parser("diagnostics")
        diagnostics_parser.add_argument("report", help="report to print diagnostics on")

        describe_parser = subparsers.add_parser("describe")
        describe_parser.add_argument("--tags", nargs="+", help="only describe tasks with the specified tags")
        describe_parser.add_argument("--tasks", nargs="+", help="only describe the specified tasks")

    @classmethod
    def summarize(cls, grading_path: Path, options: dict):
        """Summarize a batch of reports."""

        from curricula.grade.tools.summarize import summarize

        reports_path = Path(options.get("reports"))
        summarize(grading_path, tuple(reports_path.glob("*.json")))

    @classmethod
    def compare(cls, grading_path: Path, options: dict):
        """Generate a comparison of two files."""

        from curricula_grade.tools.compare import compare_output

        report_path = Path(options.get("report"))
        template_path = Path(options.get("template"))
        with path_from_options(options, change_extension(report_path, "compare.html"), batch=False).open("w") as file:
            file.write(compare_output(template_path, report_path))

    @classmethod
    def diagnostics(cls, grading_path: Path, options: dict):
        """Get diagnostics on a report."""

        assignment = GradingAssignment.read(grading_path)
        cls.diagnostics_single(assignment, Path(options.get("report")))

    @classmethod
    def diagnostics_single(cls, assignment: GradingAssignment, report_path: Path):
        """Run diagnostics on a single report."""

        from curricula_grade.tools.diagnostics import get_diagnostics
        print(get_diagnostics(assignment, report_path), end="")
