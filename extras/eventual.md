# Eventually Consistent Key-Value Store

Implementation of a distributed key-value store demonstrating eventual consistency,
based on systems like Amazon DynamoDB, Apache Cassandra, and Riak.

## Files

### Core Components

- `vector_clock.py` - Vector clock for tracking causality
- `versioned_value.py` - Values with vector clocks and timestamps
- `messages.py` - Request and response message types
- `storage_node.py` - Storage node that maintains key replicas
- `coordinator.py` - Coordinator with quorum read/write protocol
- `kv_client.py` - Client for reading and writing keys
- `partitioned_coordinator.py` - Coordinator that simulates network partitions
- `coordinator_with_read_repair.py` - Coordinator with read repair mechanism

### Examples

- `example_basic.py` - Basic read/write operations
- `example_conflict.py` - Concurrent writes creating conflicts
- `example_partition.py` - Behavior during network partition
- `example_read_repair.py` - Read repair convergence

## Requirements

Install asimpy to run the examples:

```bash
pip install asimpy
```

## Running Examples

### Basic Operations

```bash
python example_basic.py
```

Shows basic write and read operations with quorum protocol.

### Conflict Resolution

```bash
python example_conflict.py
```

Demonstrates concurrent writes creating conflicts that are resolved using
last-write-wins or application-level merging.

### Network Partitions

```bash
python example_partition.py
```

Shows how the system remains available during network partitions by requiring
only a quorum (not all replicas).

### Read Repair

```bash
python example_read_repair.py
```

Demonstrates how read repair brings lagging replicas up to date during
normal read operations.

## Key Concepts

### Vector Clocks

Vector clocks track causality between events. Each replica maintains a counter
for every replica in the system:

- When replica R performs an operation, it increments R's counter
- When receiving a message, a replica merges (takes max of) the vector clocks
- We can determine if two events are causally related or concurrent

### Quorum Protocol

For N replicas, R read quorum, W write quorum:

- Writes succeed after W nodes acknowledge
- Reads query R nodes
- If R + W > N, reads see the latest writes
- Example: N=3, R=2, W=2 tolerates 1 node failure

### Conflict Resolution

When concurrent writes create conflicts:

1. All concurrent versions are preserved
2. Client receives all versions on read
3. Client resolves conflict (last-write-wins, merging, etc.)
4. Client writes back the resolved value

### Eventual Consistency

Replicas may temporarily disagree but eventually converge through:

- **Read repair**: Fix inconsistencies discovered during reads
- **Anti-entropy**: Periodic background synchronization (not implemented)
- **Hinted handoff**: Store writes for temporarily unavailable nodes (not implemented)

## Architecture

```
Client                  Coordinator                Storage Nodes
  |                          |                      N1  N2  N3
  |---write(k,v)------------>|                      |   |   |
  |                          |---write(k,v)-------->|   |   |
  |                          |---write(k,v)------------>|   |
  |                          |<------ack----------------|   |
  |                          |<------ack--------------------|
  |<-----token,clock---------|                      |   |   |
  |                          |                      |   |   |
  |---read(k)--------------->|                      |   |   |
  |                          |---read(k)----------->|   |   |
  |                          |---read(k)--------------->|   |
  |                          |<------versions----------|   |
  |                          |<------versions--------------|
  |<-----merged_versions-----|                      |   |   |
```

## CAP Theorem Trade-offs

This implementation demonstrates the **AP** side of the CAP theorem:

- **Availability**: System continues operating during partitions
- **Partition tolerance**: Network partitions are handled gracefully
- **Eventual consistency**: Replicas may temporarily disagree

Traditional databases often choose **CP** (consistency + partition tolerance),
becoming unavailable during partitions to maintain consistency.

## Real-World Applications

- **Shopping carts**: Merge concurrent additions (Amazon)
- **Session storage**: High availability for user sessions
- **User preferences**: Eventually consistent configuration
- **Time-series data**: Metrics and logs with relaxed consistency
- **Collaborative editing**: CRDTs for conflict-free merging

## Limitations

This is a simplified implementation for educational purposes. Production systems
need additional features:

- **Merkle trees**: Efficient anti-entropy for comparing replicas
- **Hinted handoff**: Temporary storage for unavailable nodes
- **Gossip protocol**: Membership and failure detection
- **Consistent hashing**: Proper ring-based key distribution
- **Tombstones**: Deletion markers to handle concurrent deletes
- **Compaction**: Merge version history to bound storage
- **Tunable consistency**: Per-operation consistency levels
- **Multi-datacenter replication**: Geographic distribution

## Further Reading

- [Dynamo: Amazon's Highly Available Key-value Store](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- [Cassandra Documentation](https://cassandra.apache.org/doc/latest/)
- [Riak Documentation](https://riak.com/posts/technical/vector-clocks-revisited/)
- [CAP Theorem](https://en.wikipedia.org/wiki/CAP_theorem)
- [Conflict-free Replicated Data Types (CRDTs)](https://crdt.tech/)
