"""Work-stealing scheduler coordinator."""

from asimpy import Environment
from typing import List, Optional
import random
from task import Task
from worker import Worker


class WorkStealingScheduler:
    """Scheduler that coordinates work-stealing workers."""

    def __init__(self, env: Environment, num_workers: int):
        self.env = env
        self.num_workers = num_workers
        self.workers: List[Worker] = []
        self.task_counter = 0

        # Create workers
        for i in range(num_workers):
            worker = Worker(env, i, self)
            self.workers.append(worker)

    def submit_task(
        self, work_duration: float, parent_id: Optional[str] = None
    ) -> Task:
        """Submit a task to a random worker."""
        self.task_counter += 1
        task = Task(
            task_id=f"T{self.task_counter}",
            work_duration=work_duration,
            parent_id=parent_id,
        )

        # Assign to random worker (could use other strategies)
        worker = random.choice(self.workers)
        worker.deque.push_bottom(task)

        print(
            f"[{self.env.now:.1f}] Submitted {task.task_id} "
            f"to Worker {worker.worker_id}"
        )

        return task

    def get_statistics(self):
        """Get scheduler statistics."""
        total_executed = sum(w.tasks_executed for w in self.workers)
        total_stolen = sum(w.tasks_stolen for w in self.workers)

        print("\n=== Statistics ===")
        print(f"Total tasks executed: {total_executed}")
        print(f"Total tasks stolen: {total_stolen}")
        print(f"Steal rate: {100 * total_stolen / max(total_executed, 1):.1f}%")

        for worker in self.workers:
            print(
                f"Worker {worker.worker_id}: "
                f"executed={worker.tasks_executed}, "
                f"stolen={worker.tasks_stolen}, "
                f"queue={worker.deque.size()}"
            )
