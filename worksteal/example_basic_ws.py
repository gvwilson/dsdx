"""Basic work-stealing simulation."""

from asimpy import Environment
import random
from scheduler import WorkStealingScheduler


def run_basic_simulation():
    """Basic work-stealing simulation."""
    env = Environment()

    # Create scheduler with 3 workers
    scheduler = WorkStealingScheduler(env, num_workers=3)

    # Submit tasks with varying durations
    for i in range(10):
        scheduler.submit_task(work_duration=random.uniform(0.5, 2.0))

    # Run simulation
    env.run(until=20)

    # Print statistics
    scheduler.get_statistics()


if __name__ == "__main__":
    run_basic_simulation()
