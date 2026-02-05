"""Fault tolerance demonstration with worker failures."""

from asimpy import Environment, Process
from mapreduce_coordinator import MapReduceCoordinator
from mapreduce_worker import MapReduceWorker
from typing import List


def word_count_map(record: str):
    """Map function: emit (word, 1) for each word."""
    words = record.split()
    for word in words:
        yield (word.lower(), 1)


def word_count_reduce(key: str, values: List[int]) -> int:
    """Reduce function: sum all counts for a word."""
    return sum(values)


class FaultToleranceJob(Process):
    """Process that runs the MapReduce job and shows fault tolerance."""

    def init(
        self, coordinator: MapReduceCoordinator, input_data: List[str], num_splits: int
    ):
        self.coordinator = coordinator
        self.input_data = input_data
        self.num_splits = num_splits

    async def run(self):
        """Run the job and display results."""
        results = await self.coordinator.run(self.input_data, self.num_splits)

        print("\n=== Final Results ===")
        for word, count in sorted(results):
            print(f"{word}: {count}")

        print(f"\nFailed tasks: {len(self.coordinator.failed_tasks)}")


def run_fault_tolerance_test():
    """Demonstrate fault tolerance with worker failures."""
    env = Environment()

    coordinator = MapReduceCoordinator(
        env, map_fn=word_count_map, reduce_fn=word_count_reduce, num_reducers=2
    )

    # Create workers with varying failure rates
    for i in range(4):
        worker = MapReduceWorker(env, i, coordinator)
        worker.failure_rate = 0.2 if i < 2 else 0.0  # First two workers fail sometimes
        coordinator.add_worker(worker)

    input_data = [
        "hello world hello",
        "goodbye world goodbye",
        "hello goodbye hello world",
    ] * 3

    # Run job
    FaultToleranceJob(env, coordinator, input_data, num_splits=4)

    env.run(until=50)


if __name__ == "__main__":
    run_fault_tolerance_test()
