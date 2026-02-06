# MapReduce Framework

Implementation of a simplified MapReduce framework based on Google's MapReduce
and Apache Hadoop, demonstrating distributed batch processing patterns.

## Overview

MapReduce enables processing massive datasets across clusters of machines through
two simple abstractions: **map** (transform records independently) and **reduce**
(aggregate results by key). The framework handles data distribution, parallelization,
and fault tolerance, letting programmers focus on the computation logic.

## Files

### Core Framework

- `mapreduce_types.py` - Data structures (InputSplit, MapTask, ReduceTask, IntermediateData)
- `mapreduce_worker.py` - Worker executing map and reduce tasks
- `mapreduce_coordinator.py` - Coordinator orchestrating the computation
- `worker_with_combiner.py` - Worker with combiner optimization
- `coordinator_with_combiner.py` - Coordinator with combiner support
- `speculative_coordinator.py` - Coordinator with speculative execution

### Examples

- `example_word_count.py` - Classic word count example
- `example_combiner.py` - Word count with combiner optimization
- `example_fault_tolerance.py` - Handling worker failures
- `example_inverted_index.py` - Building search index

## Key Concepts

### MapReduce Phases

1. **Input Splitting**: Divide input into chunks for parallel processing
2. **Map Phase**: Transform input records to key-value pairs independently
3. **Shuffle and Sort**: Group values by key and distribute to reducers
4. **Reduce Phase**: Aggregate values for each key
5. **Output**: Collect final results

### Functional Constraints

**Map functions** must be independent (no shared state):
```python
def map_fn(record):
    for key, value in ...:
        yield (key, value)
```

**Reduce functions** must be associative and commutative:
```python
def reduce_fn(key, values):
    return aggregate(values)
```

These constraints enable parallelism and fault tolerance.

### Combiner Optimization

A combiner is a local reduce that runs on each mapper's output before shuffling:

```python
# Without combiner: 1000 pairs sent across network
map output: [(word1, 1), (word1, 1), (word1, 1), ...]

# With combiner: 10 pairs sent across network  
combiner output: [(word1, 100), (word2, 50), ...]
```

Reduces network traffic significantly for associative operations.

### Fault Tolerance

Workers are stateless. If a worker fails:
1. Coordinator detects the failure
2. Task is reassigned to another worker
3. Idempotent operations make retry safe

### Speculative Execution

Slow workers (stragglers) can delay entire job. Solution: launch backup copies
of slow tasks. First to complete wins, others are cancelled.

## Running Examples

### Word Count

```bash
python example_word_count.py
```

Counts word occurrences in text. Demonstrates basic MapReduce pattern.

### Word Count with Combiner

```bash
python example_combiner.py
```

Shows how combiner reduces network traffic by aggregating locally before shuffle.

### Fault Tolerance

```bash
python example_fault_tolerance.py
```

Demonstrates automatic retry when workers fail during task execution.

### Inverted Index

```bash
python example_inverted_index.py
```

Builds word->documents mapping for search engines. Shows MapReduce beyond counting.

## Architecture

```
Coordinator
    |
    +-- Split Input
    |
    +-- Dispatch Map Tasks --> Worker 1 (map)
    |                     |--> Worker 2 (map)
    |                     |--> Worker 3 (map)
    |
    +-- Shuffle & Sort (group by key)
    |
    +-- Dispatch Reduce Tasks --> Worker 1 (reduce partition 0)
                              |--> Worker 2 (reduce partition 1)
                              |--> Worker 3 (reduce partition 2)
```

## Real-World Applications

- **Log analysis**: Parse logs, count errors, identify patterns
- **Web indexing**: Build inverted indexes for search engines
- **Data transformation**: ETL pipelines, format conversion
- **Machine learning**: Feature extraction, distributed training
- **Graph processing**: PageRank, connected components
- **Scientific computing**: Data analysis, simulations

## Performance Considerations

### Data Locality

Production systems schedule map tasks on nodes that already have the input data,
minimizing network transfer.

### Dynamic Assignment

Don't pre-assign all tasks. Let fast workers take more work than slow ones.

### Compression

Compress intermediate data to reduce disk I/O and network usage.

### Partitioning Strategy

Hash partitioning is simple but can create skew. Production systems use
range partitioning or custom strategies for better balance.

## Limitations

MapReduce has inherent limitations that led to systems like Apache Spark:

**Disk I/O Overhead**:
- Intermediate data written to disk between phases
- Expensive for iterative algorithms (e.g., machine learning)

**Two-Phase Model**:
- Complex workflows require chaining multiple jobs
- Each job incurs full I/O overhead

**No Data Sharing**:
- Can't cache intermediate results in memory
- Each job starts from scratch

**Batch-Only**:
- Designed for batch processing
- Real-time streams need different systems

**Programming Model**:
- Only two operations (map, reduce)
- More complex patterns (join, group) are awkward

## Evolution to Spark

Apache Spark addresses MapReduce limitations:

- **In-memory processing**: Cache data between operations
- **DAG execution**: Chain operations into execution plan
- **Lazy evaluation**: Optimize entire workflow before executing
- **Rich API**: map, filter, reduce, join, groupBy, etc.
- **Unified model**: Batch, streaming, ML, graph processing

But Spark's core ideas come from MapReduce:
- Partition-based parallelism
- Functional transformations
- Fault tolerance through re-execution
- Data-parallel computation

## Production Systems

### Apache Hadoop

Open-source MapReduce implementation:
- HDFS: Distributed file system
- YARN: Resource manager
- MapReduce: Computation framework

### Google Cloud Dataflow

Google's successor to MapReduce:
- Unified batch and streaming
- Auto-scaling
- Fault-tolerant state

### Amazon EMR

Managed Hadoop/Spark service:
- Auto-scaling clusters
- Integrated with S3
- Spot instance support

## Further Reading

- [MapReduce: Simplified Data Processing on Large Clusters](https://research.google/pubs/pub62/)
- [Apache Hadoop Documentation](https://hadoop.apache.org/docs/)
- [MapReduce Design Patterns](https://www.manning.com/books/mapreduce-design-patterns)
- [Resilient Distributed Datasets (Spark paper)](https://www.usenix.org/system/files/conference/nsdi12/nsdi12-final138.pdf)
