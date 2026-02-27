"""MapReduce coordinator that orchestrates computation."""

from asimpy import Environment
import random
from typing import Callable, Any
from mr_types import MapTask, ReduceTask, IntermediateData
from mr_worker import MapReduceWorker


class MapReduceCoordinator:
    """Coordinates MapReduce computation."""

    def __init__(
        self,
        env: Environment,
        map_fn: Callable,
        reduce_fn: Callable,
        num_reducers: int = 3,
    ):
        self.env = env
        self.map_fn = map_fn
        self.reduce_fn = reduce_fn
        self.num_reducers = num_reducers

        # Workers
        self.workers: list[MapReduceWorker] = []

        # Task tracking
        self.pending_map_tasks: list[MapTask] = []
        self.pending_reduce_tasks: list[ReduceTask] = []
        self.completed_map_tasks: set = set()
        self.completed_reduce_tasks: set = set()
        self.failed_tasks: list[Any] = []

        # Intermediate data storage (indexed by partition)
        self.intermediate_storage: dict[int, IntermediateData] = {
            i: IntermediateData() for i in range(num_reducers)
        }

        # Final results
        self.results: list[tuple[Any, Any]] = []

        # Statistics
        self.map_phase_complete = False
        self.reduce_phase_complete = False
        self.start_time: float | None = None
        self.end_time: float | None = None

    def add_worker(self, worker: MapReduceWorker):
        """Register a worker."""
        self.workers.append(worker)

    def run(self, input_data: list[Any], num_splits: int):
        """Run MapReduce job on input data - returns a coroutine."""

        async def _execute():
            self.start_time = self.env.now
            print(f"[{self.env.now:.1f}] Starting MapReduce job")

            # Create map tasks from input splits
            for i, data in enumerate(self._split_input(input_data, num_splits)):
                task = MapTask(f"map_{i}", data)
                self.pending_map_tasks.append(task)

            # Dispatch map tasks
            await self._dispatch_map_tasks()

            # Wait for map phase to complete
            while not self.map_phase_complete:
                await self.env.timeout(0.5)

            print(f"\n[{self.env.now:.1f}] Map phase complete, starting reduce phase")

            # Create reduce tasks
            for i in range(self.num_reducers):
                task = ReduceTask(f"reduce_{i}", i, [])
                self.pending_reduce_tasks.append(task)

            # Dispatch reduce tasks
            await self._dispatch_reduce_tasks()

            # Wait for reduce phase to complete
            while not self.reduce_phase_complete:
                await self.env.timeout(0.5)

            self.end_time = self.env.now
            elapsed = self.end_time - self.start_time

            print(f"\n[{self.env.now:.1f}] MapReduce job complete in {elapsed:.1f}s")
            print(f"Total results: {len(self.results)}")

            return self.results

        return _execute()

    def _split_input(self, data: list[Any], num_splits: int) -> list[list[Any]]:
        """Split input data into roughly equal chunks."""
        splits = []
        chunk_size = max(1, len(data) // num_splits)

        for i in range(num_splits):
            start = i * chunk_size
            end = start + chunk_size if i < num_splits - 1 else len(data)
            splits.append(data[start:end])

        return splits

    async def _dispatch_map_tasks(self):
        """Assign map tasks to workers."""
        for task in self.pending_map_tasks:
            # Find available worker
            worker = self._get_available_worker()
            await worker.task_queue.put(task)

    async def _dispatch_reduce_tasks(self):
        """Assign reduce tasks to workers."""
        for task in self.pending_reduce_tasks:
            worker = self._get_available_worker()
            await worker.task_queue.put(task)

    def _get_available_worker(self) -> MapReduceWorker:
        """Get next available worker (round-robin)."""
        return random.choice(self.workers)

    def map_completed(
        self, task_id: str, partitions: list[IntermediateData], worker_id: int
    ):
        """Handle map task completion."""
        self.completed_map_tasks.add(task_id)

        # Store intermediate data by partition
        for i, partition_data in enumerate(partitions):
            for key, value in partition_data.pairs:
                self.intermediate_storage[i].add(key, value)

        # Check if all map tasks are done
        if len(self.completed_map_tasks) == len(self.pending_map_tasks):
            self.map_phase_complete = True

    def reduce_completed(
        self, task_id: str, results: list[tuple[Any, Any]], worker_id: int
    ):
        """Handle reduce task completion."""
        self.completed_reduce_tasks.add(task_id)
        self.results.extend(results)

        # Check if all reduce tasks are done
        if len(self.completed_reduce_tasks) == len(self.pending_reduce_tasks):
            self.reduce_phase_complete = True

    async def report_failure(self, task: Any, worker_id: int):
        """Handle task failure."""
        print(
            f"[{self.env.now:.1f}] Task {task} failed on worker {worker_id}, will retry"
        )

        self.failed_tasks.append(task)

        # Reschedule task
        worker = self._get_available_worker()
        await worker.task_queue.put(task)

    async def get_intermediate_data(self, partition_id: int) -> IntermediateData:
        """Fetch intermediate data for a partition."""
        # In real system, this would involve network transfer
        await self.env.timeout(0.1)  # Simulate network delay
        return self.intermediate_storage[partition_id]
