"""Classic word count MapReduce example."""

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


class WordCountJob(Process):
    """Process that runs the MapReduce job."""

    def init(
        self, coordinator: MapReduceCoordinator, input_data: List[str], num_splits: int
    ):
        self.coordinator = coordinator
        self.input_data = input_data
        self.num_splits = num_splits

    async def run(self):
        """Run the job and display results."""
        results = await self.coordinator.run(self.input_data, self.num_splits)

        # Sort and display results
        results.sort(key=lambda x: x[1], reverse=True)
        print("\n=== Word Count Results ===")
        for word, count in results:
            print(f"{word}: {count}")


def run_word_count():
    """Run word count example."""
    env = Environment()

    # Create coordinator
    coordinator = MapReduceCoordinator(
        env, map_fn=word_count_map, reduce_fn=word_count_reduce, num_reducers=3
    )

    # Create workers
    for i in range(4):
        worker = MapReduceWorker(env, i, coordinator)
        coordinator.add_worker(worker)

    # Input data: lines of text
    input_data = [
        "the quick brown fox",
        "jumps over the lazy dog",
        "the dog was not amused",
        "the quick brown fox jumps again",
        "the lazy dog sleeps",
    ]

    # Run job
    WordCountJob(env, coordinator, input_data, num_splits=3)

    env.run(until=50)


if __name__ == "__main__":
    run_word_count()
