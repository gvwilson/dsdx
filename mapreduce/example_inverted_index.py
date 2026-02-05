"""Inverted index construction for search engines."""

from asimpy import Environment, Process
from mapreduce_coordinator import MapReduceCoordinator
from mapreduce_worker import MapReduceWorker
from typing import Tuple, List


def inverted_index_map(record: Tuple[str, str]):
    """Map function: record is (doc_id, text)."""
    doc_id, text = record
    words = text.split()

    seen = set()
    for word in words:
        word = word.lower()
        if word not in seen:
            seen.add(word)
            yield (word, doc_id)


def inverted_index_reduce(word: str, doc_ids: List[str]) -> List[str]:
    """Reduce function: collect unique document IDs."""
    return list(set(doc_ids))


class InvertedIndexJob(Process):
    """Process that builds an inverted index."""

    def init(
        self,
        coordinator: MapReduceCoordinator,
        documents: List[Tuple[str, str]],
        num_splits: int,
    ):
        self.coordinator = coordinator
        self.documents = documents
        self.num_splits = num_splits

    async def run(self):
        """Run the job and display results."""
        results = await self.coordinator.run(self.documents, self.num_splits)

        print("\n=== Inverted Index ===")
        for word, docs in sorted(results):
            print(f"{word}: {docs}")


def run_inverted_index():
    """Build inverted index for search."""
    env = Environment()

    coordinator = MapReduceCoordinator(
        env, map_fn=inverted_index_map, reduce_fn=inverted_index_reduce, num_reducers=3
    )

    for i in range(3):
        worker = MapReduceWorker(env, i, coordinator)
        coordinator.add_worker(worker)

    # Input: (document_id, text) pairs
    documents = [
        ("doc1", "the quick brown fox"),
        ("doc2", "the lazy dog"),
        ("doc3", "the quick dog"),
        ("doc4", "brown fox and lazy dog"),
    ]

    # Run job
    InvertedIndexJob(env, coordinator, documents, num_splits=2)

    env.run(until=30)


if __name__ == "__main__":
    run_inverted_index()
