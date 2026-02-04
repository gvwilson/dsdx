"""Double-ended queue for work-stealing."""

from typing import List, Optional
from task import Task


class WorkerDeque:
    """Double-ended queue for tasks with stealing support."""

    def __init__(self):
        self.tasks: List[Task] = []

    def push_bottom(self, task: Task):
        """Owner pushes task to bottom (private end)."""
        self.tasks.append(task)

    def pop_bottom(self) -> Optional[Task]:
        """Owner pops task from bottom."""
        if not self.tasks:
            return None
        return self.tasks.pop()

    def steal_top(self) -> Optional[Task]:
        """Thief steals task from top (public end)."""
        if not self.tasks:
            return None
        return self.tasks.pop(0)

    def is_empty(self) -> bool:
        """Check if deque is empty."""
        return len(self.tasks) == 0

    def size(self) -> int:
        """Return number of tasks."""
        return len(self.tasks)
