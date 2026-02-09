"""Basic work-stealing simulation."""

import random
import sys
from asimpy import Environment
from scheduler import WorkStealingScheduler


# mccole: sim
def run_basic_simulation():
    """Basic work-stealing simulation."""
    env = Environment()

    # Create scheduler with 3 workers
    scheduler = WorkStealingScheduler(env, num_workers=3)

    # Submit tasks with varying durations
    for i in range(10):
        scheduler.submit_task(duration=random.uniform(0.5, 2.0))

    # Run simulation
    env.run(until=20)

    # Print statistics
    scheduler.get_statistics()
# mccole: /sim


if __name__ == "__main__":
    if len(sys.argv) == 2:
        random.seed(int(sys.argv[1]))
    run_basic_simulation()
