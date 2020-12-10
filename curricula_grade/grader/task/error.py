from typing import Any
from dataclasses import dataclass, asdict

__all__ = ("Error",)


@dataclass(eq=False)
class Error:
    """An error raised during a task."""

    description: str
    suggestion: str = None
    location: str = None
    traceback: str = None
    expected: Any = None
    received: Any = None

    def dump(self, thin: bool = False) -> dict:
        if thin:
            return dict(description=self.description, suggestion=self.suggestion)
        return asdict(self)

    @classmethod
    def load(cls, data: dict) -> "Error":
        return cls(**data)
