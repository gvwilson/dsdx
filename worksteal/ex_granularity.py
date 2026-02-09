"""Experiment with different task granularities."""

from asimpy import Environment
from scheduler import WorkStealingScheduler
from performance_analyzer import PerformanceAnalyzer


def run_granularity_experiment():
    """Experiment with different task granularities."""
    for granularity in [0.1, 0.5, 2.0]:
        print(f"\n{'=' * 60}")
        print(f"Testing granularity: {granularity}s")
        print("=" * 60)

        env = Environment()
        scheduler = WorkStealingScheduler(env, num_workers=4)

        PerformanceAnalyzer(
            env, scheduler, total_work=20.0, task_granularity=granularity
        )

        env.run(until=50)
        scheduler.get_statistics()


if __name__ == "__main__":
    run_granularity_experiment()
