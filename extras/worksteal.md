# Work-Stealing Scheduler

Implementation of a work-stealing task scheduler based on designs from Go's runtime,
Java's Fork/Join framework, and Cilk.

## Files

### Core Components

- `task.py` - Task representation with ID, duration, and parent tracking
- `worker_deque.py` - Double-ended queue supporting stealing
- `worker.py` - Basic worker that executes and steals tasks
- `scheduler.py` - Coordinator managing workers and task submission
- `worker_with_spawning.py` - Worker that can spawn child tasks
- `scheduler_with_spawning.py` - Scheduler with spawning workers
- `adaptive_worker.py` - Worker with smart victim selection
- `adaptive_scheduler.py` - Scheduler with adaptive workers
- `task_generator.py` - Process for generating initial tasks
- `performance_analyzer.py` - Measures performance with different granularities

### Examples

- `example_basic_ws.py` - Basic work-stealing demonstration
- `example_spawning.py` - Nested task spawning (divide-and-conquer)
- `example_adaptive.py` - Adaptive victim selection strategy
- `example_granularity.py` - Task granularity performance analysis

## Requirements

Install asimpy to run the examples:

```bash
pip install asimpy
```

## Running Examples

### Basic Work-Stealing

```bash
python example_basic_ws.py
```

Shows workers executing tasks and stealing from each other to balance load.

### Nested Task Spawning

```bash
python example_spawning.py
```

Demonstrates tasks spawning child tasks during execution, similar to
parallel divide-and-conquer algorithms.

### Adaptive Stealing

```bash
python example_adaptive.py
```

Shows a strategy that targets victims with the most work for faster
load balancing.

### Granularity Analysis

```bash
python example_granularity.py
```

Experiments with different task sizes to show the trade-off between
scheduling overhead and load balancing effectiveness.

## Key Concepts

### Work-Stealing Architecture

Each worker has a local deque:
- Owner pushes/pops from bottom (private end)
- Thieves steal from top (public end)
- Asymmetric access reduces contention

### Load Balancing

Workers automatically balance load through stealing:
- Idle workers steal from busy workers
- No central coordination needed
- Random victim selection prevents patterns

### Task Spawning

Running tasks can create child tasks:
- Children added to local deque
- May be stolen by other workers
- Natural support for divide-and-conquer

### Performance Factors

**Task Granularity**: Balance between:
- Too fine: high scheduling overhead
- Too coarse: poor load balancing

**Victim Selection**: Different strategies:
- Random: simple, avoids patterns
- Adaptive: targets busy workers first

**Queue Size**: Affects:
- Memory usage
- Stealing opportunities
- Cache behavior

## Architecture

```
Scheduler
    |
    +-- Worker 0        Worker 1        Worker 2
        |               |               |
        Deque           Deque           Deque
        [T1,T2,T3]      [T4]            []
        |               |               |
        Execute T3      Execute T4      Steal T1 from W0
        Pop bottom      Pop bottom      Steal from top
```

## Real-World Applications

- **Go runtime**: Schedules goroutines across OS threads
- **Java Fork/Join**: Parallel divide-and-conquer algorithms
- **Tokio**: Rust async runtime for futures
- **Cilk**: Parallel programming language
- **Task parallelism**: Map-reduce, parallel loops

## Implementation Notes

### Simplified for Education

This implementation focuses on concepts over performance:
- Uses simple lists instead of lock-free data structures
- Doesn't handle actual thread synchronization
- Simulates work with delays rather than real computation

### Production Considerations

Real work-stealing schedulers need:

1. **Lock-free deques**: Chase-Lev deque or similar
2. **Bounded stealing**: Prevent livelock
3. **NUMA awareness**: Prefer nearby victims for cache locality
4. **Backoff strategies**: Exponential backoff when idle
5. **Priority queues**: Handle task priorities
6. **Termination detection**: Know when all work is done
7. **Work affinity**: Keep related tasks together

## Performance Characteristics

**Advantages**:
- Scales well with worker count
- Automatic load balancing
- No central bottleneck
- Good cache behavior (mostly local access)

**Challenges**:
- Task granularity tuning
- Stealing overhead for small tasks
- Requires careful deque implementation

## Further Reading

- [Cilk: An Efficient Multithreaded Runtime System](http://supertech.csail.mit.edu/papers/PPoPP95.pdf)
- [The Chase-Lev Deque](https://www.dre.vanderbilt.edu/~schmidt/PDF/work-stealing-dequeue.pdf)
