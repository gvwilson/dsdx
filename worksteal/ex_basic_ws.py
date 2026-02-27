"""Basic work-stealing simulation."""

import random
import sys
from asimpy import Environment
from scheduler import WorkStealingScheduler


# mccole: sim
def main():
    """Basic work-stealing simulation."""
    env = Environment()

    scheduler = WorkStealingScheduler(env, num_workers=3)

    for i in range(10):
        scheduler.submit_task(duration=random.uniform(0.5, 2.0))

    env.run(until=20)

    scheduler.get_statistics()
# mccole: /sim


if __name__ == "__main__":
    if len(sys.argv) == 2:
        random.seed(int(sys.argv[1]))
    main()
