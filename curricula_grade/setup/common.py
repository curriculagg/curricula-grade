from typing import Callable, Iterable, Optional
from pathlib import Path

from curricula.library.process import TimeoutExpired
from ..grader.task import Error
from . import SetupResult


__all__ = (
    "check_file_exists",
    "search_file_by_name",
    "make_open_interactive",)


def check_file_exists(*paths: Path) -> SetupResult:
    """Check if a file is present in the directory."""

    if not any(path.exists() for path in paths):
        return SetupResult(passing=False, error=Error(description=f"can't find {paths[0].parts[-1]}"))
    return SetupResult(passing=True)


def search_file_by_name(name: str, path: Path) -> Optional[Path]:
    """Find file by name, None if none or multiple."""

    results = tuple(path.glob(f"**/{name}"))
    if len(results) == 1:
        return results[0]
    return None


def make_open_interactive(
        executable_name: str,
        count: int,
        args: Iterable[str] = (),
        cwd: Path = None,
        read_condition: Callable[[bytes], bool] = None,
        read_condition_timeout: float = None):
    """Make a method that opens interactive executables."""

    def test(resources: dict):
        try:
            for i in range(count):
                name = f"{executable_name}_i{i}"
                resources[name] = interactive = resources[executable_name].interactive(*args, cwd=cwd)
                if read_condition is not None:
                    interactive.stdout.read(condition=read_condition, timeout=read_condition_timeout)
        except OSError:
            return SetupResult(passing=False, error=Error(description="failed to open process"))
        except TimeoutExpired:
            return SetupResult(passing=False, error=Error(description=f"{executable_name} timed out"))

    return test
