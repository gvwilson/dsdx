"""Scheduler with adaptive workers."""

from asimpy import Environment
from typing import List
from scheduler import WorkStealingScheduler
from adaptive_worker import AdaptiveWorker


class AdaptiveScheduler(WorkStealingScheduler):
    """Scheduler with adaptive workers."""

    def __init__(self, env: Environment, num_workers: int):
        self.env = env
        self.num_workers = num_workers
        self.workers: List[AdaptiveWorker] = []
        self.task_counter = 0

        for i in range(num_workers):
            worker = AdaptiveWorker(env, i, self)
            self.workers.append(worker)
