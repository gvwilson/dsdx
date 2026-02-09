"""Experiment with different task granularities."""

import random
import sys
from asimpy import Environment
from scheduler import WorkStealingScheduler
from performance_analyzer import PerformanceAnalyzer


def run_granularity_experiment():
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
    if len(sys.argv) == 2:
        random.seed(int(sys.argv[1]))
    run_granularity_experiment()
