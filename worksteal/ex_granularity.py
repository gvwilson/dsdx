"""Experiment with different task granularities."""

from asimpy import Environment
from scheduler import WorkStealingScheduler
from performance_analyzer import PerformanceAnalyzer
from dsdx import dsdx


def main():
    """Experiment with different task granularities."""
    for granularity in [0.1, 0.5, 2.0]:
        env = Environment()
        scheduler = WorkStealingScheduler(env, num_workers=4, verbose=False)
        PerformanceAnalyzer(
            env, scheduler, total_work=50.0, task_granularity=granularity
        )
        env.run(until=100)
        scheduler.get_statistics()
        print()


if __name__ == "__main__":
    dsdx(main)
