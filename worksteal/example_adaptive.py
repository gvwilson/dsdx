"""Simulation with adaptive stealing strategy."""

from asimpy import Environment
import random
from adaptive_scheduler import AdaptiveScheduler
from task import Task


def run_adaptive_simulation():
    """Demonstrate adaptive stealing strategy."""
    env = Environment()

    scheduler = AdaptiveScheduler(env, num_workers=4)

    # Create imbalanced initial load
    for i in range(15):
        # Give most tasks to worker 0
        worker_idx = 0 if i < 12 else random.randint(0, 3)
        scheduler.workers[worker_idx].deque.push_bottom(
            Task(f"T{i + 1}", random.uniform(1.0, 2.0))
        )

    print("Initial load distribution:")
    for worker in scheduler.workers:
        print(f"  Worker {worker.worker_id}: {worker.deque.size()} tasks")

    env.run(until=25)
    scheduler.get_statistics()


if __name__ == "__main__":
    run_adaptive_simulation()
