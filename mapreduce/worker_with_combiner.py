"""MapReduce worker with combiner optimization."""

from mapreduce_worker import MapReduceWorker
from mapreduce_types import MapTask, IntermediateData


class WorkerWithCombiner(MapReduceWorker):
    """Worker that applies combiner to map output."""

    async def execute_map(self, task: MapTask):
        """Execute map task with local combining."""
        self.current_task = task
        self.maps_executed += 1

        print(f"[{self.now:.1f}] Worker {self.worker_id}: Starting {task}")

        processing_time = len(task.input_split.data) * 0.1
        await self.timeout(processing_time)

        # Apply map function
        intermediate = IntermediateData()
        for record in task.input_split.data:
            for key, value in self.coordinator.map_fn(record):
                intermediate.add(key, value)

        # Apply combiner locally
        if hasattr(self.coordinator, "combiner_fn") and self.coordinator.combiner_fn:
            grouped = intermediate.group_by_key()
            combined = IntermediateData()

            for key, values in grouped.items():
                combined_value = self.coordinator.combiner_fn(key, values)
                combined.add(key, combined_value)

            intermediate = combined

            print(
                f"[{self.now:.1f}] Worker {self.worker_id}: "
                f"Combiner reduced to {len(intermediate.pairs)} pairs"
            )

        # Partition intermediate data
        partitions = intermediate.partition(self.coordinator.num_reducers)

        print(f"[{self.now:.1f}] Worker {self.worker_id}: Completed {task}")

        await self.coordinator.map_completed(task.task_id, partitions, self.worker_id)
        self.current_task = None
