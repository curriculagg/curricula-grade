from typing import Type, Set, Optional, Union
from decimal import Decimal

from . import Result


class TaskProfile:
    """Static presets under which a task is registered."""

    details: Optional[dict] = None
    graded: Optional[bool] = None
    weight: Optional[Union[Decimal, int, float]] = None
    tags: Optional[Set[str]] = None
    result_type: Type[Result]
