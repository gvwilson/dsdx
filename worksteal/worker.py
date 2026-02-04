"""Worker process for work-stealing scheduler."""

from asimpy import Process
from typing import Optional, TYPE_CHECKING
import random
from task import Task
from worker_deque import WorkerDeque

if TYPE_CHECKING:
    from scheduler import WorkStealingScheduler


class Worker(Process):
    """Worker that executes tasks with work-stealing."""

    def init(self, worker_id: int, scheduler: "WorkStealingScheduler"):
        self.worker_id = worker_id
        self.scheduler = scheduler
        self.deque = WorkerDeque()
        self.tasks_executed = 0
        self.tasks_stolen = 0
        self.current_task: Optional[Task] = None

    async def run(self):
        """Main worker loop: execute local tasks or steal."""
        while True:
            # Try to get a task from local deque
            task = self.deque.pop_bottom()

            if task:
                # Execute local task
                await self.execute_task(task)
            else:
                # No local work, try stealing
                stolen = await self.try_steal()

                if stolen:
                    await self.execute_task(stolen)
                else:
                    # No work available anywhere, wait a bit
                    await self.timeout(0.1)

    async def execute_task(self, task: Task):
        """Execute a task."""
        self.current_task = task
        self.tasks_executed += 1

        print(
            f"[{self.now:.1f}] Worker {self.worker_id}: "
            f"Executing {task.task_id} (queue size: {self.deque.size()})"
        )

        # Simulate work
        await self.timeout(task.work_duration)

        print(f"[{self.now:.1f}] Worker {self.worker_id}: Completed {task.task_id}")

        self.current_task = None

    async def try_steal(self) -> Optional[Task]:
        """Try to steal a task from another worker."""
        # Random victim selection
        victims = [w for w in self.scheduler.workers if w != self]

        if not victims:
            return None

        # Shuffle to avoid patterns
        random.shuffle(victims)

        for victim in victims:
            task = victim.deque.steal_top()
            if task:
                self.tasks_stolen += 1
                print(
                    f"[{self.now:.1f}] Worker {self.worker_id}: "
                    f"Stole {task.task_id} from Worker {victim.worker_id}"
                )
                return task

        return None

    def spawn_task(self, task: Task):
        """Spawn a new task (called by executing task)."""
        self.deque.push_bottom(task)
        print(f"[{self.now:.1f}] Worker {self.worker_id}: Spawned {task.task_id}")
