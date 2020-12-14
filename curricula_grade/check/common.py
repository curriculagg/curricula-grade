from typing import Optional
from pathlib import Path

from ..grader.task.error import Error
from . import CheckResult

__all__ = ("check_file_exists", "search_file_by_name")


def check_file_exists(*paths: Path) -> CheckResult:
    """Check if a file is present in the directory."""

    if not any(path.exists() for path in paths):
        return CheckResult(passing=False, error=Error(description=f"can't find {paths[0].parts[-1]}"))
    return CheckResult(passing=True)


def search_file_by_name(name: str, path: Path) -> Optional[Path]:
    """Find file by name, None if none or multiple."""

    results = tuple(path.glob(f"**/{name}"))
    if len(results) == 1:
        return results[0]
    return None
