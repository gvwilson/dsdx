# MapReduce Framework

[](b:Dean2004) introduced the MapReduce framework,
which allowed programmers to perform many different data processing tasks
by using two abstractions called (as you might guess) map and reduce.
[Hadoop][hadoop], [Apache Spark][apache-spark], and other tools
embody the same model,
which is a good starting point for learning about distributed systems.

## The MapReduce Pattern {: #mapreduce-pattern}

MapReduce works by breaking computation into two phases.
The *map* phase transforms input records independently,
while the subsequent *reduce* phase combines results that have the same key.
Between these phases the framework handles shuffling data across machines,
sorting by key,
and managing failures.
Each MapReduce computation consists of:

1.  Input splitting: the input data is divided into chunks.
1.  Map phase: a user-supplied function is applied to each input record to produce key-value pairs.
1.  Shuffle: all values with the same key are grouped together and distributed to reducers.
1.  Reduce phase: the values associated with each key are processed to produce the final results.
1.  Output: the results are saved somewhere.

In order for this to work,
map operations must be independent,
i.e.,
there cannot be any shared state
so that the operations can be done anywhere, in any order.
Similarly,
the reduce operations must be associative and commutative
so that they can be applied in any order.
These two constraints enable parallelism and fault tolerance.

## Core Data Structures

Let's start with some dataclasses to represent the data flowing through the framework.
Input will be split into chunks for the map phase:

<div data-inc="mr_types.py" data-filter="inc=map"></div>

Intermediate data will be partitioned for reducers:

<div data-inc="mr_types.py" data-filter="inc=intermediate"></div>

And finally,
intermediate chunks will be reduced:

<div data-inc="mr_types.py" data-filter="inc=reduce"></div>

<div class="callout" markdown="1">

The initial implementation of MapReduce contained a subtle bug.
Python's built-in function `hash` generates a [hash code](g:hash-code)
from a chunk of data.
That value is partially randomized:
it is the same within any run of a program,
but may differ from one run to the next.
This meant that different runs of our simulations
sent different chunks of data to different places,
which in turn meant that runs weren't reproducible.
To fix this,
we introduced our own hashing function:

<div data-inc="mr_types.py" data-filter="inc=hash"></div>

</div>

## Worker Implementation

Worker processes execute both map and reduce tasks.
Each has a unique worker ID,
a queue of incoming tasks,
and a reference to the overall work coordinator:

<div data-inc="mr_worker.py" data-filter="inc=worker"></div>

The code shown above also records a few simple statistics
and can simulate failure with a specified probability;
we will use this last propery when we look at fault tolerance.

When a worker runs,
it repeatedly gets a task from its queue and executes it.
If there's a simulated failure,
the worker reports that back to the coordinator instead:

<div data-inc="mr_worker.py" data-filter="inc=run"></div>

Each map task consists of one or more records.
For simplicity's sake we assume each record needs the same processing time,
so after waiting that long,
the worker partitions the results
and sends them back to the coordinator:

<div data-inc="mr_worker.py" data-filter="inc=map"></div>

Reducing works the same way:

<div data-inc="mr_worker.py" data-filter="inc=reduce"></div>

## MapReduce Coordinator

The coordinator orchestrates the entire computation:

<div data-inc="mr_coordinator.py"></div>

The coordinator manages the entire lifecycle:
splitting input, dispatching tasks, collecting results, and handling failures by re-executing failed tasks.

Note that `run()` returns a coroutine (by returning the result of `_execute()`), which must be awaited.
This pattern allows the coordinator to be a regular object (not a Process) while still providing async execution.
A Process wraps the coroutine to integrate it into the simulation.

## Example: Word Count

The classic MapReduce example counts occurrences of each word in a document:

<div data-inc="ex_word_count.py"></div>

This demonstrates MapReduce's power: the programmer writes two simple functions (map and reduce),
wraps the job execution in a Process,
and the framework handles distribution, parallelization, and aggregation.

## Combiner Functions

A combiner is a local reduce that runs on each mapper's output before shuffling.
This reduces network traffic:

<div data-inc="coordinator_with_combiner.py"></div>

The combiner reduces data before it crosses the network,
which can dramatically improve performance for operations like summation or counting.

## Handling Stragglers with Speculative Execution

Some workers may be slow (stragglers) due to hardware issues, resource contention, or other reasons.
MapReduce handles this with speculative execution—launching backup copies of slow tasks:

<div data-inc="speculative_coordinator.py"></div>

Speculative execution ensures one slow worker doesn't delay the entire job.
The first copy to complete wins; others are discarded.

## Fault Tolerance Simulation

Let's simulate worker failures:

<div data-inc="ex_fault_tolerance.py"></div>

The framework automatically retries failed tasks, ensuring computation completes despite failures.

## Real-World Example: Inverted Index

An inverted index maps words to documents—essential for search engines:

<div data-inc="ex_inverted_index.py"></div>

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

## A Note on Hashing and Reproducibility {: #mapreduce-hashing}

The `IntermediateData.partition` method assigns each key to a reducer
using a hash function.
An earlier version of this code used Python's built-in `hash()`,
which meant that the examples produced different output every time they were run
even when `random.seed()` was called with the same value.
The reason is that Python randomizes string hashing on startup:
the environment variable `PYTHONHASHSEED` is set to a different random value
each time the interpreter starts,
so `hash("the")` returns a different integer in every process.
This is a security measure to prevent hash collision attacks,
but it means that `hash()` is not suitable for partitioning
when reproducibility matters.
The fix is to use `hashlib.md5` (or another deterministic hash function)
to convert keys to integers.
The result is not affected by `PYTHONHASHSEED`,
so the examples produce the same output every time.
