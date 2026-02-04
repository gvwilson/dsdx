"""Task representation for work-stealing scheduler."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Task:
    """A unit of work to be executed."""

    task_id: str
    work_duration: float
    parent_id: Optional[str] = None  # For nested tasks

    def __str__(self):
        return f"Task({self.task_id})"
