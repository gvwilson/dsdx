"""Task generator for spawning simulations."""

from asimpy import Process
import random
from scheduler import WorkStealingScheduler


class TaskGenerator(Process):
    """Generates tasks including ones that spawn subtasks."""

    def init(self, scheduler: WorkStealingScheduler, num_initial_tasks: int):
        self.scheduler = scheduler
        self.num_initial_tasks = num_initial_tasks

    async def run(self):
        """Generate initial tasks."""
        for i in range(self.num_initial_tasks):
            self.scheduler.submit_task(work_duration=random.uniform(1.0, 3.0))
            await self.timeout(0.5)
