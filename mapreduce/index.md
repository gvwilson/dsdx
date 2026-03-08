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

## Word Count {: #mapreduce-wordcount}

Let's start by showing how MapReduce is used,
and then show how it is implemented.
The classic MapReduce example counts how often each word occurs in a document.

<div data-inc="ex_word_count.py"></div>

As this example shows,
he programmer writes two simple functions and runs a process to coordinate them.
The framework handles distribution, parallelization, and aggregation.

## Core Data Structures {: #mapreduce-datastructures}

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

## Worker Implementation {: #mapreduce-worker}

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

## MapReduce Coordinator {: #mapreduce-coordinator}

The coordinator manages the entire lifecycle:
splitting input, dispatching tasks, collecting results, and handling failures by re-executing failed tasks.

<div data-inc="mr_coordinator.py"></div>

Note that `run()` returns a coroutine by returning the result of `_execute()`;
this coroutine is awaited by the `Process` that the user writes.

## Combiner Functions {: #mapreduce-combiner}

A combiner is a local reduce that runs on each mapper's output before shuffling
in order to reduce network traffic.
Doing this can dramatically improve performance for operations like summation or counting.

<div data-inc="coordinator_with_combiner.py"></div>

## Handling Stragglers with Speculative Execution {: #mapreduce-speculative}

Some workers may be stragglers due to hardware issues or resource contention.
MapReduce can accommodate this by launching backup copies of slow tasks.
The first copy to complete wins,
while others are discarded.
This is called [speculative execution](g:speculative-execution),
and ensures that one slow worker doesn't delay the entire job.

<div data-inc="speculative_coordinator.py"></div>

## Fault Tolerance Simulation {: #mapreduce-fault}

A simple extension of speculative execution is [fault tolerance](g:fault-tolerance):
the framework automatically retries failed tasks,
ensuring that computation completes despite failures.

<div data-inc="ex_fault_tolerance.py"></div>

## In the Real World {: #mapreduce-real}

MapReduce's limitations led to the next-generation systems described in the introduction.
First, MapReduce writes intermediate data to disk between phases.
This is expensive for iterative algorithms of the kind used in machine learning,
and becomes more so when complex computation require multiple MapReduce jobs to be chained together.

Second, MapReduce has no data sharing:
there is no way to cache intermediate results in memory across jobs,
which can lead to redundant computation.
Finally, MapReduce is designed for batch processing:
real-time stream processing requires a different approach.

Even with these shortcomings,
MapReduce demonstrates how to build scalable distributed computation through simple abstractions.
The key principles are:

1.  Partitioning: data is automatically partitioned and distributed.
1.  Independent processing: Map tasks don't communicate, and reduce tasks are independent.
1.  Fault tolerance: Idempotent operations make it safe to re-execute tasks.
1.  Simplicity: Programmers write two functions, and the framework handles everything else.

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
