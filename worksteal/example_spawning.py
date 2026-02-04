"""Simulation with nested task spawning."""

from asimpy import Environment
from scheduler_with_spawning import SchedulerWithSpawning
from task_generator import TaskGenerator


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


if __name__ == "__main__":
    run_spawning_simulation()
