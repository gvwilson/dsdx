# Conflict-Free Replicated Data Types (CRDTs)

Implementation of CRDTs for partition-tolerant, eventually consistent distributed systems,
based on data structures used in Google Docs, Figma, and Riak.

## Overview

CRDTs are data structures that can be updated independently on different replicas and
merged without conflicts, achieving strong eventual consistency. They eliminate the need
for consensus in certain scenarios by using mathematical properties (commutativity,
associativity, idempotence) to guarantee convergence.

## Files

### Core CRDT Implementations

- `gcounter.py` - Grow-only counter (state-based)
- `pncounter.py` - Positive-Negative counter supporting increment/decrement
- `lwwregister.py` - Last-Write-Wins register for single values
- `orset.py` - Observed-Remove Set for add/remove operations
- `opbased_counter.py` - Operation-based counter (CmRDT)

### Replication and Synchronization

- `crdt_replica.py` - Replica maintaining CRDT state with sync
- `crdt_workload.py` - Workload generator for CRDT operations
- `partitioned_crdt_replica.py` - Replica with partition support
- `partition_manager.py` - Manages network partitions

### Examples

- `example_basic_crdt.py` - Basic CRDT convergence demonstration
- `example_partition_crdt.py` - CRDT behavior during network partition

## Key Concepts

### Strong Eventual Consistency

CRDTs guarantee that replicas receiving the same updates converge to the same state,
regardless of update order, network delays, or partitions.

**Properties:**
- **Eventual delivery**: Every update reaches every replica eventually
- **Convergence**: Replicas with same updates have same state
- **No conflicts**: Concurrent updates merge automatically

### State-Based vs Operation-Based

**State-based CRDTs (CvRDTs)**:
- Replicas send entire state
- Merge must be commutative, associative, idempotent
- Higher network overhead
- Simpler to reason about

**Operation-based CRDTs (CmRDTs)**:
- Replicas send operations (deltas)
- Operations must commute
- Lower network overhead
- Requires reliable delivery

### CRDT Types

**G-Counter (Grow-only Counter)**:
- Only increments
- Each replica tracks its own count
- Merge takes maximum of each replica's count
- O(replicas) space

**PN-Counter (Positive-Negative Counter)**:
- Supports increment and decrement
- Two G-Counters: one for +, one for -
- Value = increments - decrements
- O(replicas) space

**LWW-Register (Last-Write-Wins Register)**:
- Single value with timestamp
- Concurrent writes: highest timestamp wins
- May lose updates (last-write-wins semantics)
- O(1) space

**OR-Set (Observed-Remove Set)**:
- Add/remove elements
- Each add gets unique tag
- Remove deletes all observed tags
- Add-wins: concurrent add/remove keeps element
- O(elements × adds) space

## Running Examples

### Basic Convergence

```bash
python example_basic_crdt.py
```

Shows three replicas making concurrent updates to counters, registers, and sets.
After synchronization, all replicas converge to the same state.

### Network Partition

```bash
python example_partition_crdt.py
```

Demonstrates CRDTs handling a network partition. Replicas update independently
during partition, then converge when partition heals.

## Architecture

```
Replica 1           Replica 2           Replica 3
  Counter             Counter             Counter
  Register            Register            Register
  Set                 Set                 Set
    |                   |                   |
    |---sync state----->|                   |
    |<--sync state------|                   |
    |                   |---sync state----->|
    |<--sync state------|                   |
```

## Real-World Applications

- **Collaborative editing**: Google Docs, Figma (text CRDTs like RGA, LSeq)
- **Distributed databases**: Riak (OR-Set, LWW-Register, counters)
- **Offline-first mobile apps**: Sync when connected, work offline
- **Real-time collaboration**: Multiplayer games, shared whiteboards
- **Edge computing**: Low-latency updates without cross-datacenter coordination
- **Shopping carts**: Merge concurrent adds/removes across sessions

## CRDT Properties

### Commutativity
Operations can be applied in any order:
```
A + B = B + A
add(x); add(y) = add(y); add(x)
```

### Associativity
Grouping doesn't matter:
```
(A + B) + C = A + (B + C)
merge(merge(s1, s2), s3) = merge(s1, merge(s2, s3))
```

### Idempotence
Applying same operation multiple times = applying once:
```
A + A = A
merge(s, s) = s
```

## Trade-offs

**Advantages:**
- No coordination needed for updates
- Always available (AP in CAP theorem)
- Partition tolerant
- Offline-capable
- Low latency

**Disadvantages:**
- Metadata overhead (vector clocks, tags)
- Eventual consistency (not immediate)
- Application must handle semantics (e.g., LWW loses updates)
- Garbage collection needed for long-running systems

## Comparison with Other Approaches

| Approach | Coordination | Latency | Availability | Consistency |
|----------|-------------|---------|--------------|-------------|
| CRDTs | None | Low | High | Eventual |
| Consensus (Raft/Paxos) | High | High | Medium | Strong |
| Locks | High | High | Low | Strong |
| Last-write-wins | None | Low | High | Weak |

## Production Considerations

Real CRDT systems need:

- **Garbage collection**: Compact metadata over time
- **Delta-state CRDTs**: Send only recent changes
- **Causal delivery**: Operations delivered in causal order
- **Compression**: Reduce vector clock and tag overhead
- **Custom CRDTs**: Application-specific merge semantics
- **Hybrid approaches**: CRDTs for some data, consensus for others

## CRDT Library Comparison

**Automerge**: JavaScript CRDT library for JSON-like data
**Yjs**: High-performance CRDT for collaborative editing
**Riak**: Distributed database with built-in CRDTs
**Redis Enterprise**: Geo-replicated CRDTs (counters, sets)
**Akka Distributed Data**: CRDTs for Akka actors

## Further Reading

- [CRDTs: Consistency without concurrency control](https://arxiv.org/abs/0907.0929)
- [A comprehensive study of CRDTs](https://hal.inria.fr/inria-00555588)
- [Automerge Documentation](https://automerge.org/)
- [CRDT Tech](https://crdt.tech/)
- [Riak CRDT Documentation](https://docs.riak.com/riak/kv/latest/developing/data-types/)
