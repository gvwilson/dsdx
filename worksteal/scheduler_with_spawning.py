"""Scheduler using workers that can spawn tasks."""

from asimpy import Environment
from typing import List
from scheduler import WorkStealingScheduler
from worker_with_spawning import WorkerWithSpawning


class SchedulerWithSpawning(WorkStealingScheduler):
    """Scheduler using workers that can spawn tasks."""

    def __init__(self, env: Environment, num_workers: int):
        self.env = env
        self.num_workers = num_workers
        self.workers: List[WorkerWithSpawning] = []
        self.task_counter = 0

        # Create workers with spawning capability
        for i in range(num_workers):
            worker = WorkerWithSpawning(env, i, self)
            self.workers.append(worker)
