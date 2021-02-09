# Curricula Grade

The other half of `curricula`'s core functionality is automated grading.
In order to use automated grading, material writers have to implement tests using the `curricula_grade` toolkit.
Automated grading for individual problems can be combined into composite assignments, complete with problem weights and other metadata.

## Writing Tests

While somewhat bulkier than unit-test frameworks, the additional syntax and runtime overhead backing the `Grader` make it much easier to generate and manage reports for students.
Let's walk through an [example](https://github.com/curriculagg/curricula-material-sample/).
Note that we'll be using `curricula_grade_cpp` as our example assignment is written in C++, but the framework itself is language-agnostic.

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

### Checks

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

### Compilation

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

Next, we'll actually run a test:

### Tests

```python
@grader.register()
def test_simple_addition(binary: ExecutableFile) -> CorrectnessResult:
    """Check 1 + 1."""

    runtime = binary.execute("1", "1")
    if runtime.stdout.strip() != b"2":
        return CorrectnessResult(
            passing=False,
            actual=runtime.stdout.strip().decode(),
            expected="2",
            error=Error(description="incorrect result"),
            details=dict(runtime=runtime.dump()))
    return CorrectnessResult(passing=True)
```

This is an actual test case, and it affirms any given submission writes the sum of the first two arguments to `stdout`.
In a proper problem, there will most likely be many more of these.
In the first line of the runnable body, we invoke the compiled binary in a subprocess, passing two arguments: `1` and `1`.
Let's take a look at an example submission:

```cpp
#include <iostream>

using namespace std;

int main(int argc, char** argv)
{
    cout << stoi(argv[1]) + stoi(argv[2]) << endl;
    return 0;
}
```

We can determine whether this submission prints what we expect it to by comparing the `runtime.stdout`.
If it's not `2`, we return a failing result with some extra details on what happened.
Otherwise, we return a passing result.

### Cleanup

Finally, let's add a cleanup task to avoid leaving extraneous files in our submissions.
The only thing we have to do is delete our binary, which we can again ask for via injected arguments:

```python
@grader.register[CleanupResult](tags={"sanity"}, graded=False)
def cleanup_submission(binary: ExecutableFile):
    """Delete the binary."""

    delete_file(binary.path)
````

Notice something new is going on here: instead of using the return annotation, we're providing the result type via bracket notation in the registration decorator.
Why?
If a runnable returns None, the task executor will attempt to instantiate a default `result_type`.
In this case, it will substitute a `CleanupResult.default()` for the result automatically.
It would not be semantically correct to use a return annotation on this runnable because it does not return anything, and so a secondary mechanism is provided to specify `result_type`, i.e. `grader.register[result_type]`.

### Summary

The entire grading script is as follows:

```python
from curricula_grade.shortcuts import *
from curricula_grade.setup.common import check_file_exists
from curricula_grade_cpp.setup.common.gpp import gpp_compile_object
from curricula.library.files import delete_file

from pathlib import Path

root = Path(__file__).absolute().parent
grader = Grader()

GPP_OPTIONS = ("-std=c++14", "-Wall")


@grader.register(tags={"sanity"}, graded=False)
def check_submission(submission: Submission, resources: dict) -> SetupResult:
    """Check submission.cpp is present."""

    header_path = resources["source"] = submission.problem_path.joinpath("submission.cpp")
    return check_file_exists(header_path)


@grader.register(passing={"check_submission"}, tags={"sanity"}, graded=False)
def build_submission(source: Path, resources: dict) -> SetupResult:
    """Compile the submission."""

    result, resources["binary"] = gpp_compile_object(
        source,
        destination_path=source.parent.joinpath("binary"),
        gpp_options=GPP_OPTIONS)
    return result


@grader.register()
def test_simple_addition(binary: ExecutableFile) -> CorrectnessResult:
    """Check 1 + 1."""

    runtime = binary.execute("1", "1")
    if runtime.stdout.strip() != b"2":
        return CorrectnessResult(
            passing=False,
            actual=runtime.stdout.strip().decode(),
            expected="2",
            error=Error(description="incorrect result"),
            details=dict(runtime=runtime.dump()))
    return CorrectnessResult(passing=True)


@grader.register[CleanupResult](tags={"sanity"}, graded=False)
def cleanup_submission(binary: ExecutableFile):
    """Delete the binary."""

    delete_file(binary.path)
```

## Running the Grader

In order to grade an assignment, you will first need to make sure that you've constructed the grading artifact correctly.
It is recommended you use [`curricula-compile`](https://github.com/curriculagg/curricula-compile) for this, but if you insist on doing it manually, the following directory structure is required:

```
grading/
  index.json
  problem1/
    tests.py
    ...
  problem2/
    tests.py
    ...
  ...
```

Once you've created the grading artifact, you can run grading from the command line.
Currently, the options are as follow:

```
usage: curricula grade run [-h] --grading GRADING [--skip] [--report] [--concise] [--progress] [--sample SAMPLE] [--tags TAGS [TAGS ...]] [--tasks TASKS [TASKS ...]] [--summarize] [--thin] [--amend]
                           (-f FILE | -d DIRECTORY)
                           submissions [submissions ...]

positional arguments:
  submissions           run tests on a single target

optional arguments:
  -h, --help            show this help message and exit
  --grading GRADING, -g GRADING
                        the grading artifact
  --skip                skip reports that have already been run
  --report, -r          whether to log test results
  --concise, -c         whether to report concisely
  --progress, -p        show progress in batch
  --sample SAMPLE       randomly sample batch
  --tags TAGS [TAGS ...]
                        only run tasks with the specified tags
  --tasks TASKS [TASKS ...]
                        only run the specified tasks
  --summarize           summarize after running batch
  --thin                shorten output for space
  --amend               amend any existing report at the destination
  -f FILE, --file FILE  output file for single report
  -d DIRECTORY, --directory DIRECTORY
                        where to write reports to if batched
```

If you have all of the submissions in a folder by username, i.e. `submissions/noahbkim` etc., you would do something like this:

```shell
$ curricula grade run --grading grading/ --progress --concise --summarize submissions/*/ -d reports/
```

Once the grader is finished, there will be a `*.report.json` file in `reports/` corresponding to each of the submissions in the arguments.
You can then use included tools to format these reports in Markdown, etc.

## Grader Output

Grading an assignment will yield a serializable `AssignmentReport`, which is composed of `ProblemReport` objects for each problem graded automatically.
This report, formatted as JSON, will look something like this:

```json
{
  "problem": {
    "short": "test",
    "title": "Test"
  },
  "automated": {
    "partial": false,
    "results": {
      "check_submission": {
        "complete": true,
        "passing": true,
        "score": null,
        "error": null,
        "messages": [],
        "task": {
          "name": "check_submission",
          "description": "Check submission.cpp is present."
        },
        "details": {}
      },
      "build_submission": {
        "complete": true,
        "passing": true,
        "score": null,
        "error": null,
        "messages": [],
        "task": {
          "name": "build_submission",
          "description": "Compile the submission."
        },
        "details": {
          "runtime": {
            "args": [
              "g++",
              "/Users/noahbkim/Repositories/curricula/curricula-grade-cpp/example/submission.cpp",
              "-std=c++14",
              "-Wall",
              "-o",
              "/Users/noahbkim/Repositories/curricula/curricula-grade-cpp/example/binary"
            ],
            "cwd": null,
            "stdin": null,
            "stdout": "",
            "stderr": "",
            "elapsed": 1.189917291,
            "code": 0,
            "timeout": null,
            "timed_out": false,
            "raised_exception": false,
            "exception": null
          }
        }
      },
      "test_simple_addition": {
        "complete": true,
        "passing": true,
        "score": null,
        "error": null,
        "messages": [],
        "task": {
          "name": "test_simple_addition",
          "description": "Check 1 + 1."
        },
        "details": {},
        "expected": null,
        "actual": null
      },
      "cleanup_submission": {
        "complete": true,
        "passing": true,
        "score": null,
        "error": null,
        "messages": [],
        "task": {
          "name": "cleanup_submission",
          "description": "Delete the binary."
        },
        "details": {}
      }
    }
  }
}
```
