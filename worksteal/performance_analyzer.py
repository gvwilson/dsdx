"""Performance analyzer for granularity experiments."""

from asimpy import Process
from typing import Optional
from scheduler import WorkStealingScheduler


class PerformanceAnalyzer(Process):
    """Analyzes scheduler performance with different granularities."""

    def init(
        self,
        scheduler: WorkStealingScheduler,
        total_work: float,
        task_granularity: float,
    ):
        self.scheduler = scheduler
        self.total_work = total_work
        self.task_granularity = task_granularity
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    async def run(self):
        """Submit tasks and measure completion time."""
        self.start_time = self.now

        num_tasks = int(self.total_work / self.task_granularity)

        print(
            f"\n[{self.now:.1f}] Starting: {num_tasks} tasks "
            f"of {self.task_granularity}s each"
        )

        for i in range(num_tasks):
            self.scheduler.submit_task(self.task_granularity)

        # Wait for all workers to become idle
        while True:
            await self.timeout(1.0)

            all_idle = all(
                w.deque.is_empty() and w.current_task is None
                for w in self.scheduler.workers
            )

            if all_idle:
                self.end_time = self.now
                break

        elapsed = self.end_time - self.start_time
        speedup = self.total_work / elapsed
        efficiency = speedup / self.scheduler.num_workers

        print("\n=== Performance Analysis ===")
        print(f"Granularity: {self.task_granularity}s")
        print(f"Total work: {self.total_work}s")
        print(f"Wall time: {elapsed:.2f}s")
        print(f"Speedup: {speedup:.2f}x")
        print(f"Efficiency: {efficiency:.1%}")
