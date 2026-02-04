"""Worker with adaptive victim selection strategy."""

from typing import Optional
from worker import Worker
from task import Task


class AdaptiveWorker(Worker):
    """Worker with adaptive victim selection."""

    def init(self, worker_id: int, scheduler):
        super().init(worker_id, scheduler)
        self.steal_attempts = 0
        self.failed_steals = 0

    async def try_steal(self) -> Optional[Task]:
        """Try to steal with adaptive victim selection."""
        self.steal_attempts += 1

        # Try workers with largest queues first
        victims = [w for w in self.scheduler.workers if w != self]
        victims.sort(key=lambda w: w.deque.size(), reverse=True)

        for victim in victims:
            if victim.deque.size() > 0:
                task = victim.deque.steal_top()
                if task:
                    self.tasks_stolen += 1
                    print(
                        f"[{self.now:.1f}] Worker {self.worker_id}: "
                        f"Stole {task.task_id} from Worker {victim.worker_id} "
                        f"(victim queue: {victim.deque.size()})"
                    )
                    return task

        self.failed_steals += 1
        return None
