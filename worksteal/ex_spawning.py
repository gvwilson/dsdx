"""Simulation with nested task spawning."""

import random
import sys
from asimpy import Environment
from scheduler_with_spawning import SchedulerWithSpawning
from task_generator import TaskGenerator


# mccole: sim
def run_spawning_simulation():
    """Demonstrate nested task spawning."""
    env = Environment()

    # Create scheduler with spawning workers
    scheduler = SchedulerWithSpawning(env, num_workers=4)

    # Generate initial tasks
    TaskGenerator(env, scheduler, num_initial_tasks=5)

    # Run simulation
    env.run(until=30)

    # Print statistics
    scheduler.get_statistics()
# mccole: /sim


if __name__ == "__main__":
    if len(sys.argv) == 2:
        random.seed(int(sys.argv[1]))
    run_spawning_simulation()
