"""Core data structures for MapReduce framework."""

from dataclasses import dataclass, field
from typing import List, Tuple, Any, Dict
from collections import defaultdict


@dataclass
class InputSplit:
    """A partition of input data."""

    split_id: int
    data: List[Any]

    def __str__(self):
        return f"Split{self.split_id}(size={len(self.data)})"


@dataclass
class MapTask:
    """A map task to be executed."""

    task_id: str
    input_split: InputSplit

    def __str__(self):
        return f"MapTask({self.task_id})"


@dataclass
class ReduceTask:
    """A reduce task to be executed."""

    task_id: str
    partition_id: int
    keys: List[Any]  # Keys this reducer is responsible for

    def __str__(self):
        return f"ReduceTask({self.task_id}, partition={self.partition_id})"


@dataclass
class IntermediateData:
    """Intermediate key-value pairs from map phase."""

    pairs: List[Tuple[Any, Any]] = field(default_factory=list)

    def add(self, key: Any, value: Any):
        """Add a key-value pair."""
        self.pairs.append((key, value))

    def partition(self, num_partitions: int) -> List["IntermediateData"]:
        """Partition by key hash."""
        partitions = [IntermediateData() for _ in range(num_partitions)]

        for key, value in self.pairs:
            partition_id = hash(key) % num_partitions
            partitions[partition_id].add(key, value)

        return partitions

    def group_by_key(self) -> Dict[Any, List[Any]]:
        """Group values by key."""
        grouped = defaultdict(list)
        for key, value in self.pairs:
            grouped[key].append(value)
        return dict(grouped)
