import importlib.util
from curricula_grade.shortcuts import *

grader = Grader()


@grader.register(tags={"sanity"})
def import_submission(submission: Submission, resources: dict) -> SetupResult:
    """Add the submission to resources."""

    submission_path = submission.problem_path.joinpath("submission.py")

    try:
        spec = importlib.util.spec_from_file_location("_submission", str(submission_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except ImportError:
        return SetupResult(passing=False, error=Error(description="could not import submission"))

    resources["module"] = module
    return SetupResult(passing=True)


@grader.register(tags={"sanity"}, passing={"import_submission"})
def test_one_plus_one(module) -> CorrectnessResult:
    """Check if 1 + 1 = 2."""

    return CorrectnessResult(passing=module.add(1, 1) == 2)


# Ignore this, added so that example can be tested.
if __name__ == '__main__':
    import json
    from pathlib import Path
    from curricula_grade.models import GradingProblem

    root = Path(__file__).absolute().parent
    grader.problem = GradingProblem(short="test", title="Test")
    report = grader.run(context=Context(), submission=Submission(problem_path=root, assignment_path=root))

    print(json.dumps(report.dump(), indent=2))
