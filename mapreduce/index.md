# MapReduce Framework

In 2004, Google published a paper that changed how we think about processing large datasets.
The MapReduce framework made it possible for programmers to process terabytes of data
across thousands of machines without worrying about parallelization,
fault tolerance,
or data distribution.
By providing two simple abstractions—map and reduce—the framework handles
all the distributed systems complexity behind the scenes.

Hadoop brought MapReduce to the open-source world,
powering early data processing at companies like Yahoo, Facebook, and Twitter.
While newer frameworks like Apache Spark have largely superseded MapReduce,
understanding this pattern remains essential,
as it demonstrates fundamental principles of distributed computation
that appear throughout modern data processing systems.

MapReduce works by breaking computation into two phases:
*map* transforms input records independently,
and *reduce* aggregates results by key.
Between these phases the framework handles shuffling data across machines,
sorting by key,
and managing failures.
This simple model enables processing massive datasets with relatively simple code.

## The MapReduce Pattern

The MapReduce computation model consists of:

1.  **Input splitting**: Divide the input into chunks
1.  **Map phase**: Apply a function to each input record, producing key-value pairs
1.  **Shuffle and sort**: Group all values by key and distribute to reducers
1.  **Reduce phase**: Process each key's values to produce final output
1.  **Output**: Write results

The power comes from constraints:
map operations must be independent (no shared state between maps),
and reduce operations must be associative and commutative (can be applied in any order).
These constraints enable parallelism and fault tolerance.

## Core Data Structures

Let's start with the basic types:

```python
from asimpy import Environment, Process, Queue
from typing import List, Dict, Tuple, Callable, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import random


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
    
    def partition(self, num_partitions: int) -> List['IntermediateData']:
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
```

These structures represent the data flowing through the framework.
Input is split into chunks, map tasks process splits, and intermediate data is partitioned for reducers.

## Worker Implementation

Workers execute map and reduce tasks:

```python
class MapReduceWorker(Process):
    """Worker that executes map and reduce tasks."""
    
    def init(self, worker_id: int, coordinator: 'MapReduceCoordinator'):
        self.worker_id = worker_id
        self.coordinator = coordinator
        self.task_queue = Queue(self._env)
        
        # Statistics
        self.maps_executed = 0
        self.reduces_executed = 0
        self.current_task: Optional[Any] = None
        
        # Simulate failure probability
        self.failure_rate = 0.0
    
    async def run(self):
        """Main worker loop: fetch and execute tasks."""
        while True:
            # Get task from queue
            task = await self.task_queue.get()
            
            # Check for simulated failure
            if random.random() < self.failure_rate:
                print(f"[{self.now:.1f}] Worker {self.worker_id}: FAILED during {task}")
                await self.coordinator.report_failure(task, self.worker_id)
                continue
            
            # Execute task
            if isinstance(task, MapTask):
                await self.execute_map(task)
            elif isinstance(task, ReduceTask):
                await self.execute_reduce(task)
    
    async def execute_map(self, task: MapTask):
        """Execute a map task."""
        self.current_task = task
        self.maps_executed += 1
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Starting {task} with {len(task.input_split.data)} records")
        
        # Simulate processing time
        processing_time = len(task.input_split.data) * 0.1
        await self.timeout(processing_time)
        
        # Apply map function
        intermediate = IntermediateData()
        for record in task.input_split.data:
            for key, value in self.coordinator.map_fn(record):
                intermediate.add(key, value)
        
        # Partition intermediate data
        partitions = intermediate.partition(self.coordinator.num_reducers)
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Completed {task}, produced {len(intermediate.pairs)} pairs")
        
        # Send results to coordinator
        await self.coordinator.map_completed(task.task_id, partitions, self.worker_id)
        
        self.current_task = None
    
    async def execute_reduce(self, task: ReduceTask):
        """Execute a reduce task."""
        self.current_task = task
        self.reduces_executed += 1
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Starting {task}")
        
        # Fetch intermediate data for this partition
        intermediate_data = await self.coordinator.get_intermediate_data(task.partition_id)
        
        # Group by key
        grouped = intermediate_data.group_by_key()
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Processing {len(grouped)} keys")
        
        # Simulate processing time
        processing_time = len(grouped) * 0.1
        await self.timeout(processing_time)
        
        # Apply reduce function
        results = []
        for key, values in grouped.items():
            result = self.coordinator.reduce_fn(key, values)
            results.append((key, result))
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Completed {task}, produced {len(results)} results")
        
        # Send results to coordinator
        await self.coordinator.reduce_completed(task.task_id, results, self.worker_id)
        
        self.current_task = None
```

Workers are stateless—they fetch tasks, execute them, and report results.
If a worker fails, the coordinator can reassign the task to another worker.

## MapReduce Coordinator

The coordinator orchestrates the entire computation:

```python
class MapReduceCoordinator:
    """Coordinates MapReduce computation."""
    
    def __init__(self, env: Environment, 
                 map_fn: Callable, 
                 reduce_fn: Callable,
                 num_reducers: int = 3):
        self.env = env
        self.map_fn = map_fn
        self.reduce_fn = reduce_fn
        self.num_reducers = num_reducers
        
        # Workers
        self.workers: List[MapReduceWorker] = []
        
        # Task tracking
        self.pending_map_tasks: List[MapTask] = []
        self.pending_reduce_tasks: List[ReduceTask] = []
        self.completed_map_tasks: set = set()
        self.completed_reduce_tasks: set = set()
        self.failed_tasks: List[Any] = []
        
        # Intermediate data storage (indexed by partition)
        self.intermediate_storage: Dict[int, IntermediateData] = {
            i: IntermediateData() for i in range(num_reducers)
        }
        
        # Final results
        self.results: List[Tuple[Any, Any]] = []
        
        # Statistics
        self.map_phase_complete = False
        self.reduce_phase_complete = False
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def add_worker(self, worker: MapReduceWorker):
        """Register a worker."""
        self.workers.append(worker)
    
    def run(self, input_data: List[Any], num_splits: int):
        """Run MapReduce job on input data - returns a coroutine."""
        async def _execute():
            self.start_time = self.env.now
            print(f"[{self.env.now:.1f}] Starting MapReduce job")
            
            # Split input data
            splits = self._split_input(input_data, num_splits)
            
            # Create map tasks
            for i, split in enumerate(splits):
                task = MapTask(f"map_{i}", split)
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
    
    def _split_input(self, data: List[Any], num_splits: int) -> List[InputSplit]:
        """Split input data into roughly equal chunks."""
        splits = []
        chunk_size = max(1, len(data) // num_splits)
        
        for i in range(num_splits):
            start = i * chunk_size
            end = start + chunk_size if i < num_splits - 1 else len(data)
            splits.append(InputSplit(i, data[start:end]))
        
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
    
    async def map_completed(self, task_id: str, partitions: List[IntermediateData], 
                           worker_id: int):
        """Handle map task completion."""
        self.completed_map_tasks.add(task_id)
        
        # Store intermediate data by partition
        for i, partition_data in enumerate(partitions):
            for key, value in partition_data.pairs:
                self.intermediate_storage[i].add(key, value)
        
        # Check if all map tasks are done
        if len(self.completed_map_tasks) == len(self.pending_map_tasks):
            self.map_phase_complete = True
    
    async def reduce_completed(self, task_id: str, results: List[Tuple[Any, Any]], 
                              worker_id: int):
        """Handle reduce task completion."""
        self.completed_reduce_tasks.add(task_id)
        self.results.extend(results)
        
        # Check if all reduce tasks are done
        if len(self.completed_reduce_tasks) == len(self.pending_reduce_tasks):
            self.reduce_phase_complete = True
    
    async def report_failure(self, task: Any, worker_id: int):
        """Handle task failure."""
        print(f"[{self.env.now:.1f}] Task {task} failed on worker {worker_id}, "
              f"will retry")
        
        self.failed_tasks.append(task)
        
        # Reschedule task
        worker = self._get_available_worker()
        await worker.task_queue.put(task)
    
    async def get_intermediate_data(self, partition_id: int) -> IntermediateData:
        """Fetch intermediate data for a partition."""
        # In real system, this would involve network transfer
        await self.env.timeout(0.1)  # Simulate network delay
        return self.intermediate_storage[partition_id]
```

The coordinator manages the entire lifecycle:
splitting input, dispatching tasks, collecting results, and handling failures by re-executing failed tasks.

Note that `run()` returns a coroutine (by returning the result of `_execute()`), which must be awaited.
This pattern allows the coordinator to be a regular object (not a Process) while still providing async execution.
A Process wraps the coroutine to integrate it into the simulation.

## Example: Word Count

The classic MapReduce example is word count—count occurrences of each word in a document:

```python
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
    
    def init(self, coordinator: MapReduceCoordinator, 
             input_data: List[str], num_splits: int):
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
        env,
        map_fn=word_count_map,
        reduce_fn=word_count_reduce,
        num_reducers=3
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
    
    # Run job (creates a Process that orchestrates the computation)
    WordCountJob(env, coordinator, input_data, num_splits=3)
    
    env.run(until=50)


if __name__ == "__main__":
    run_word_count()
```

This demonstrates MapReduce's power: the programmer writes two simple functions (map and reduce),
wraps the job execution in a Process,
and the framework handles distribution, parallelization, and aggregation.

## Combiner Functions

A combiner is a local reduce that runs on each mapper's output before shuffling.
This reduces network traffic:

```python
class MapReduceCoordinatorWithCombiner(MapReduceCoordinator):
    """Coordinator with combiner support."""
    
    def __init__(self, env: Environment, 
                 map_fn: Callable, 
                 reduce_fn: Callable,
                 combiner_fn: Optional[Callable] = None,
                 num_reducers: int = 3):
        super().__init__(env, map_fn, reduce_fn, num_reducers)
        self.combiner_fn = combiner_fn or reduce_fn


class WorkerWithCombiner(MapReduceWorker):
    """Worker that applies combiner to map output."""
    
    async def execute_map(self, task: MapTask):
        """Execute map task with local combining."""
        self.current_task = task
        self.maps_executed += 1
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Starting {task}")
        
        processing_time = len(task.input_split.data) * 0.1
        await self.timeout(processing_time)
        
        # Apply map function
        intermediate = IntermediateData()
        for record in task.input_split.data:
            for key, value in self.coordinator.map_fn(record):
                intermediate.add(key, value)
        
        # Apply combiner locally
        if self.coordinator.combiner_fn:
            grouped = intermediate.group_by_key()
            combined = IntermediateData()
            
            for key, values in grouped.items():
                combined_value = self.coordinator.combiner_fn(key, values)
                combined.add(key, combined_value)
            
            intermediate = combined
            
            print(f"[{self.now:.1f}] Worker {self.worker_id}: "
                  f"Combiner reduced to {len(intermediate.pairs)} pairs")
        
        # Partition intermediate data
        partitions = intermediate.partition(self.coordinator.num_reducers)
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Completed {task}")
        
        await self.coordinator.map_completed(task.task_id, partitions, self.worker_id)
        self.current_task = None


def run_word_count_with_combiner():
    """Word count with combiner optimization."""
    env = Environment()
    
    # Combiner is same as reducer for word count
    coordinator = MapReduceCoordinatorWithCombiner(
        env,
        map_fn=word_count_map,
        reduce_fn=word_count_reduce,
        combiner_fn=word_count_reduce,  # Sum locally before shuffle
        num_reducers=3
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
    
    # Create job process
    class CombinerJob(Process):
        def init(self, coordinator, input_data, num_splits):
            self.coordinator = coordinator
            self.input_data = input_data
            self.num_splits = num_splits
        
        async def run(self):
            results = await self.coordinator.run(self.input_data, self.num_splits)
            print(f"\n=== Results: {len(results)} unique words ===")
    
    CombinerJob(env, coordinator, input_data, num_splits=6)
    env.run(until=50)


if __name__ == "__main__":
    run_word_count_with_combiner()
```

The combiner reduces data before it crosses the network,
which can dramatically improve performance for operations like summation or counting.

## Handling Stragglers with Speculative Execution

Some workers may be slow (stragglers) due to hardware issues, resource contention, or other reasons.
MapReduce handles this with speculative execution—launching backup copies of slow tasks:

```python
class SpeculativeCoordinator(MapReduceCoordinator):
    """Coordinator with speculative execution for stragglers."""
    
    def __init__(self, env: Environment, 
                 map_fn: Callable, 
                 reduce_fn: Callable,
                 num_reducers: int = 3,
                 speculative_threshold: float = 5.0):
        super().__init__(env, map_fn, reduce_fn, num_reducers)
        self.speculative_threshold = speculative_threshold
        self.task_start_times: Dict[str, float] = {}
        self.speculative_tasks: set = set()
    
    async def _dispatch_map_tasks(self):
        """Dispatch map tasks with speculative execution."""
        await super()._dispatch_map_tasks()
        
        # Start monitoring for stragglers
        async def monitor_stragglers():
            while not self.map_phase_complete:
                await self.env.timeout(1.0)
                await self._check_for_stragglers()
        
        self.env.process(monitor_stragglers())
    
    async def _check_for_stragglers(self):
        """Launch speculative tasks for stragglers."""
        now = self.env.now
        
        for task in self.pending_map_tasks:
            if task.task_id in self.completed_map_tasks:
                continue
            
            if task.task_id not in self.task_start_times:
                self.task_start_times[task.task_id] = now
                continue
            
            elapsed = now - self.task_start_times[task.task_id]
            
            if (elapsed > self.speculative_threshold and 
                task.task_id not in self.speculative_tasks):
                
                print(f"[{now:.1f}] Launching speculative copy of {task.task_id}")
                self.speculative_tasks.add(task.task_id)
                
                # Launch backup copy
                worker = self._get_available_worker()
                await worker.task_queue.put(task)
```

Speculative execution ensures one slow worker doesn't delay the entire job.
The first copy to complete wins; others are discarded.

## Fault Tolerance Simulation

Let's simulate worker failures:

```python
def run_fault_tolerance_test():
    """Demonstrate fault tolerance with worker failures."""
    env = Environment()
    
    coordinator = MapReduceCoordinator(
        env,
        map_fn=word_count_map,
        reduce_fn=word_count_reduce,
        num_reducers=2
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
    
    # Create job process
    class FaultToleranceJob(Process):
        def init(self, coordinator, input_data, num_splits):
            self.coordinator = coordinator
            self.input_data = input_data
            self.num_splits = num_splits
        
        async def run(self):
            results = await self.coordinator.run(self.input_data, self.num_splits)
            
            print("\n=== Final Results ===")
            for word, count in sorted(results):
                print(f"{word}: {count}")
            
            print(f"\nFailed tasks: {len(self.coordinator.failed_tasks)}")
    
    FaultToleranceJob(env, coordinator, input_data, num_splits=4)
    env.run(until=50)


if __name__ == "__main__":
    run_fault_tolerance_test()
```

The framework automatically retries failed tasks, ensuring computation completes despite failures.

## Real-World Example: Inverted Index

An inverted index maps words to documents—essential for search engines:

```python
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


def run_inverted_index():
    """Build inverted index for search."""
    env = Environment()
    
    coordinator = MapReduceCoordinator(
        env,
        map_fn=inverted_index_map,
        reduce_fn=inverted_index_reduce,
        num_reducers=3
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
    
    # Create job process
    class InvertedIndexJob(Process):
        def init(self, coordinator, documents, num_splits):
            self.coordinator = coordinator
            self.documents = documents
            self.num_splits = num_splits
        
        async def run(self):
            results = await self.coordinator.run(self.documents, self.num_splits)
            
            print("\n=== Inverted Index ===")
            for word, docs in sorted(results):
                print(f"{word}: {docs}")
    
    InvertedIndexJob(env, coordinator, documents, num_splits=2)
    env.run(until=30)


if __name__ == "__main__":
    run_inverted_index()
```

This shows how MapReduce handles complex analytics beyond simple aggregation.

## Limitations and Evolution

MapReduce has limitations that led to systems like Apache Spark:

-  **Disk I/O overhead**: MapReduce writes intermediate data to disk between phases.
For iterative algorithms (like machine learning), this is expensive.

-  **Two-phase limitation**: Complex computations require chaining multiple MapReduce jobs,
each with full disk I/O overhead.

-  **No data sharing**: Each job starts from scratch.
No way to cache intermediate results in memory across jobs.

-  **Batch-only**: MapReduce is designed for batch processing.
Real-time stream processing requires different systems.

Spark addresses these limitations with in-memory processing,
lazy evaluation,
and a more flexible computational model.
But MapReduce's core ideas remain fundamental:
functional transformations,
partition-based parallelism,
and fault tolerance through re-execution.

## Real-World Considerations

Production MapReduce systems need:

-  **Locality-aware scheduling**:
Schedule tasks on nodes that already have the input data (data locality) to minimize network transfer.

-  **Dynamic task assignment**:
Don't pre-assign all tasks; let fast workers take more work than slow ones.

-  **Compression**:
Compress intermediate data to reduce disk and network usage.

-  **Counters and monitoring**:
Track progress, identify bottlenecks, report statistics.

-  **Job prioritization**:
Schedule important jobs before less important ones.

-  **Resource management**:
Integrate with cluster resource managers (YARN, Mesos).

-  **Security**:
Authentication, authorization, data encryption.

## Conclusion

MapReduce demonstrates how to build scalable distributed computation through simple abstractions.
The key principles are:

1.  **Functional programming**: Map and reduce are pure functions with no side effects
1.  **Partitioning**: Data is automatically partitioned and distributed
1.  **Independent processing**: Map tasks don't communicate; reduce tasks are independent
1.  **Fault tolerance**: Re-execute failed tasks; idempotent operations make this safe
1.  **Simplicity**: Programmers write two functions; framework handles everything else

These patterns appear throughout distributed computing: Spark uses similar transformations, Flink extends the model to streams, and data warehouse systems like BigQuery use map-reduce-style execution plans.

Our simulation demonstrates the core mechanics: splitting input, distributing tasks, shuffling data, and handling failures.
While real implementations require sophisticated optimizations—network protocols, disk management, resource scheduling—the fundamental pattern we've built captures the essence of distributed batch processing.
