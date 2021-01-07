# Curricula Grade

Grading is the other half of `curricula`'s core functionality.
In order to use automated grading, material writers have to implement tests using the `curricula_grade` toolkit.

## Writing Tests

While somewhat bulkier than unit-test frameworks, the additional mechanisms backing the `Grader` make it much easier to generate and manage reports for students.
Let's walk through an [example](https://github.com/curriculagg/curricula-material-sample/).

```python3
from curricula_grade.shortcuts import *
from curricula_grade.setup.common import check_file_exists
from curricula_grade.test.correctness.common import ProcessCompareExitCodeTest
from curricula_grade_cpp import Paths
from curricula_grade_cpp.setup.common.gpp import gpp_compile_object
from curricula.library.files import delete_file

from pathlib import Path

root = Path(__file__).absolute().parent
grader = Grader()

GPP_OPTIONS = ("-std=c++14", "-Wall")
````

To start off, we include `pathlib` for convenient, file-system-independent path operations.
We also include several utilities from `curricula_grade` that define `g++` command line options we'll use later.
Finally, we'll initialize the grader for this problem.
First, we'll check and make sure that the file we're expecting the student to submit is present in the submission:

```python3
@grader.register(tags={"sanity"})
def check_decimal_header(submission: Submission, resources: dict) -> SetupResult:
    """decimal.hpp present in decimal/"""

    header_path = resources["decimal"] = submission.problem_path.joinpath("decimal.hpp")
    return check_file_exists(header_path)
```

Here, we register a `check` task in the `setup` phase of the grader.
The `sanity` option indicates that if we run grading on a submission with `--sanity`, this task will be run.
Note that parameters in tasks are injected, but can also be accessed manually through the `resources` dictionary (`resources['resources'] is resources`).
In this task, we store the source path of file we're expecting to grade for this problem.
However, if it doesn't exist, the returned `CorrectnessResult` will indicate to the grader that this task has failed, and that any dependent tasks should not be executed.

```python
@grader.setup.compile(dependency="check_hello_world", sanity=True)
def build_hello_world(hello_world_source_path: Path, resources: dict):
    """Compile the program with gcc."""

    resources["hello_world_path"] = Path("/tmp", "hello_world")
    result, resources["hello_world"] = build_gpp_executable(
        source_path=hello_world_source_path,
        destination_path=resources["hello_world_path"],
        gpp_options=GPP_OPTIONS)
    return result
```

This segment builds the submitted `hello_world.cpp` file with `g++`.
As specified by the registration decorator, this task depends on `check_hello_world` passing.
If a task has multiple dependencies, `dependencies=["check_hello_world", ...]` may be used instead.
In the task method, a custom `ExecutableFile` will be inserted into `resources`, and the `BuildResult` from the build function will be returned to the grader.
Note that both [`build_gpp_exectuable`](curricula/grade/setup/build/common.py) and [`check_file_exists`](curricula/grade/setup/check/common.py) are just convenience methods that reduce code.

```python
@grader.test.correctness(dependency="build_hello_world")
def test_hello_world_output(hello_world: ExecutableFile):
    """Check if the program outputs as expected."""

    runtime = hello_world.execute(timeout=1)
    return CorrectnessResult(passed=runtime.stdout.strip() == b"Hello, world!", runtime=runtime.dump())
```

This is an actual test cases.
In a proper problem, there will most likely be many more of these.
Note that since there's no `sanity=True` in the registration decorator, this test will not be run if the grader is sanity-checking a solution.
Here, we simply invoke the built binary `hello_world`.
If what's outputted to `stdout` during its runtime is `"Hello, world!"`, the `CorrectnessResult` will indicate the case passed.

For an individual problem, this whole harness might seem somewhat bulky.
However, note that the registration decorator can be used inline to register a generated task.
In other words, test cases that simply compare input and output files can simply be dynamically registered with a for loop rather than be written out manually.

```python
@grader.teardown.cleanup(dependency="build_hello_world")
def cleanup_hello_world(hello_world_path: Path):
    """Clean up executables."""

    if hello_world_path.is_file():
        files.delete_file(hello_world_path)
````

In this last segment, the built binary is deleted.
Not returning a result in a task registered in the `teardown` phase will cause the grader to generate a default `TeardownResult` with a passing status.
Note that `build_hello_world`, `test_hello_world_output`, and `cleanup_hello_world` all depend on `build_hello_world`.
If the latter does not pass, neither will any of the former.

## Grader Output

Grading an assignment will yield a serializable `AssignmentReport`, which is composed of `ProblemReport` objects for each problem graded automatically.
For the `hello_world` solution, the following report was generated.

```json
{
  "hello_world": {
    "check_hello_world": {
      "complete": true,
      "passed": true,
      "task": "check_hello_world",
      "details": {}
    },
    "build_hello_world": {
      "complete": true,
      "passed": true,
      "task": "build_hello_world",
      "details": {
        "runtime": {
          "args": [
            "g++",
            "-Wall",
            "-std=c++11",
            "-o",
            "/tmp/hello_world",
            "artifacts/assignment/solution/hello_world/hello_world.cpp"
          ],
          "timeout": null,
          "code": 0,
          "elapsed": 0.21283740003127605,
          "stdin": null,
          "stdout": "",
          "stderr": "",
          "timed_out": false,
          "raised_exception": false,
          "exception": null
        }
      }
    },
    "test_hello_world_output": {
      "complete": true,
      "passed": true,
      "task": "test_hello_world_output",
      "details": {
        "runtime": {
          "args": [
            "/tmp/hello_world"
          ],
          "timeout": 1,
          "code": 0,
          "elapsed": 0.0011609999928623438,
          "stdin": null,
          "stdout": "Hello, world!\n",
          "stderr": "",
          "timed_out": false,
          "raised_exception": false,
          "exception": null
        }
      }
    },
    "cleanup_hello_world": {
      "complete": true,
      "passed": true,
      "task": "cleanup_hello_world",
      "details": {}
    }
  }
}
```

Note that this report matches up key-wise with the grading artifact `grading.json` file:

```json
{
  "hello_world": {
    "title": "Hello, World!",
    "directory": "hello_world",
    "percentage": 0.1,
    "tasks": {
      "check_hello_world": {
        "name": "check_hello_world",
        "description": "Check whether hello_world.cpp has been submitted.",
        "stage": "setup",
        "kind": "check",
        "dependencies": [],
        "details": {
          "sanity": true
        }
      },
      "build_hello_world": {
        "name": "build_hello_world",
        "description": "Compile the program with gcc.",
        "stage": "setup",
        "kind": "build",
        "dependencies": [
          "check_hello_world"
        ],
        "details": {
          "sanity": true
        }
      },
      "test_hello_world_output": {
        "name": "test_hello_world_output",
        "description": "Check if the program outputs as expected.",
        "stage": "test",
        "kind": "correctness",
        "dependencies": [
          "build_hello_world"
        ],
        "details": {}
      },
      "cleanup_hello_world": {
        "name": "cleanup_hello_world",
        "description": "Clean up executables.",
        "stage": "teardown",
        "kind": "cleanup",
        "dependencies": [
          "build_hello_world"
        ],
        "details": {}
      }
    }
  }
}
```

Using these two data sources, the grader can format each report into a readable file.
This functionality is provided in the `tools` package of `curricula.grade`.
