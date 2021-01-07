# Curricula Grade

The other half of `curricula`'s core functionality is automated grading.
In order to use automated grading, material writers have to implement tests using the `curricula_grade` toolkit.

## Writing Tests

While somewhat bulkier than unit-test frameworks, the additional syntax and runtime overhead backing the `Grader` make it much easier to generate and manage reports for students.
Let's walk through an [example](https://github.com/curriculagg/curricula-material-sample/).

```python3
from curricula_grade.shortcuts import *
from curricula_grade.setup.common import check_file_exists
from curricula_grade_cpp.setup.common.gpp import gpp_compile_object
from curricula.library.files import delete_file

from pathlib import Path

root = Path(__file__).absolute().parent
grader = Grader()

GPP_OPTIONS = ("-std=c++14", "-Wall")
````

To start off, we include several basic utilities from `curricula_grade`.
We also import two commons functions, `check_file_exists` and `gpp_compile_object`.
Lastly, we include `delete_file` and `Path` for generalized file system access.

Using our imports, we create a `Grader` instance to register tasks to.
The `root` and `GPP_OPTIONS` are just constants for reference that we'll use for convenience later.
With the boilerplate out of the way, we start by writing a task that checks if a file we're expecting the student to implement is present in the submission:

```python3
@grader.register(tags={"sanity"}, graded=False)
def check_submission(submission: Submission, resources: dict) -> SetupResult:
    """Check submission.cpp is present."""

    header_path = resources["source"] = submission.problem_path.joinpath("submission.cpp")
    return check_file_exists(header_path)
```

The first thing to notice is the `grader.register` decorator we're using.
This line indicates to the grader that we want it to run this function, which we'll refer to generally as a runnable, during grading.
Of the several ways we can register a task to a grader, this is the simplest.

The arguments passed to `grader.register` define metadata about the task.
In this particular case, we're only specifying a tag that the task falls under.
We can use tags to specify subsets of tasks to run while grading, which can be useful for sanity checks in an online submission, etc.
Other metadata that can be assigned in the registration call include the task name and description, which default to the function name and docstring.

When a task is executed, it looks at the arguments in its runnable's signature and injects the corresponding resources from the resource pool by name.
We ask for the full resources `dict` by including `resources` as a parameter to the runnable.
By default, `resources` contains:

- A `Submission`, which describes the submission currently being graded.
- A `Context`, which includes options passed to the grader, either from the command line or otherwise.
- A reference to the `resources` map itself.
- Anything we put in the `resources` map manually.
  In this particular task, we're putting a new item called `source` into the resource map that points to the path to the file we want to grade.
  This simply makes it easier to reference later; we can just include a `source` parameter in the `Runnable` signature.

The last important detail in this example is the annotated return type of the runnable, `SetupResult`.
Because we may find ourselves deserializing grading results down the road (to summarize a batch, generate a formatted report, etc.), we need to be able to determine what kind of `Result` subclass we're expecting without executing the runnable.
If we use a decorator to register the runnable, it must either have an annotated return type, an attribute `result_type`, or you must subscript the registrar with the result type.

Let's move on to compiling our submission.

```python3
@grader.register(passing={"check_submission"}, tags={"sanity"}, graded=False)
def build_submission(source: Path, resources: dict) -> SetupResult:
    """Compile the submission."""

    result, resources["binary"] = gpp_compile_object(
        source,
        destination_path=source.parent.joinpath("binary"),
        gpp_options=GPP_OPTIONS)
    return result
```

This segment builds a file `submission.cpp` in a target directory using `g++`.
As specified by the registrar invocation, this task depends on `check_submission` passing.
If `check_submission` returns a `SetupResult(passing=False)`, this task will never be executed.

Our call to `gpp_compile_object` here does exactly what you might expect: invokes `g++` in a subprocess to compile the C++ file.
You can take a look at the source in the [`curricula_grade_cpp`](https://github.com/curriculagg/curricula-grade-cpp/blob/master/curricula_grade_cpp/setup/common/gpp.py) library.
Notice that nothing there is particularly fancy or magical; it's simply boilerplate I've encapsulated for convenience.

Next, we'll actually run a test.

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
