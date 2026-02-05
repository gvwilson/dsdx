"""Word count with combiner optimization."""

from asimpy import Environment, Process
from coordinator_with_combiner import MapReduceCoordinatorWithCombiner
from worker_with_combiner import WorkerWithCombiner
from typing import List


def word_count_map(record: str):
    """Map function: emit (word, 1) for each word."""
    words = record.split()
    for word in words:
        yield (word.lower(), 1)


def word_count_reduce(key: str, values: List[int]) -> int:
    """Reduce function: sum all counts for a word."""
    return sum(values)


class CombinerJob(Process):
    """Process that runs the MapReduce job with combiner."""

    def init(
        self,
        coordinator: MapReduceCoordinatorWithCombiner,
        input_data: List[str],
        num_splits: int,
    ):
        self.coordinator = coordinator
        self.input_data = input_data
        self.num_splits = num_splits

    async def run(self):
        """Run the job and display results."""
        results = await self.coordinator.run(self.input_data, self.num_splits)
        print(f"\n=== Results: {len(results)} unique words ===")


def run_word_count_with_combiner():
    """Word count with combiner optimization."""
    env = Environment()

    # Combiner is same as reducer for word count
    coordinator = MapReduceCoordinatorWithCombiner(
        env,
        map_fn=word_count_map,
        reduce_fn=word_count_reduce,
        combiner_fn=word_count_reduce,  # Sum locally before shuffle
        num_reducers=3,
    )

    # Create workers with combiner support
    for i in range(4):
        worker = WorkerWithCombiner(env, i, coordinator)
        coordinator.add_worker(worker)

    # Larger input to show combiner benefit
    input_data = [
        "the quick brown fox " * 10,
        "jumps over the lazy dog " * 10,
        "the dog was not amused " * 10,
    ] * 5

    # Run job
    CombinerJob(env, coordinator, input_data, num_splits=6)

    env.run(until=50)


if __name__ == "__main__":
    run_word_count_with_combiner()
