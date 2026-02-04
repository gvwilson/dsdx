# Distributed Lock Manager

Implementation of a distributed lock service demonstrating key concepts from
systems like Apache ZooKeeper, etcd, and Google Chubby.

## Overview

This chapter shows how distributed locks enable mutual exclusion across multiple
machines, handling network partitions, process failures, and clock skew. The
implementation demonstrates lease-based locking, fencing tokens to prevent
split-brain scenarios, and simplified consensus for maintaining consistent state.

## Files

### Core Components

- `basic_lock_server.py` - Lock server with lease-based locking
- `lock_client.py` - Basic client that acquires and releases locks
- `failing_client.py` - Client that simulates crashes
- `protected_resource.py` - Resource that validates fencing tokens
- `fenced_client.py` - Client with fencing token support
- `replicated_lock_manager.py` - Manager coordinating multiple lock servers
- `replicated_lock_client.py` - Client for replicated lock manager

### Examples

- `example_basic.py` - Basic lock competition between clients
- `example_failure.py` - Lease expiration after client failure
- `example_fencing.py` - Fencing tokens preventing split-brain
- `example_replicated.py` - Replicated lock manager with fault tolerance

## Key Concepts

### Lease-Based Locking

Locks have time-limited leases that expire automatically. This prevents locks
from being held forever if a client crashes. Clients can renew leases to keep
locks longer.

**Why leases?**
- Client crashes don't deadlock the system
- Network partitions are handled gracefully
- No need for complex failure detection

### Fencing Tokens

Each lock acquisition gets a monotonically increasing token number. Protected
resources check tokens and reject access from clients with stale (lower) tokens.
This prevents zombie processes from corrupting resources.

**Split-brain scenario without fencing:**
1. Client A acquires lock (token 1)
2. Client A pauses (GC, network partition)
3. Lease expires, Client B acquires lock (token 2)
4. Client A wakes up, still thinks it has the lock
5. Both clients access resource → corruption

**With fencing:**
- Client A's access is rejected (token 1 < 2)
- Resource only accepts highest token seen
- Safety maintained despite timing issues

### Replication

Multiple lock servers maintain the same state. Clients must get approval from
a majority of servers to acquire a lock. This provides fault tolerance - the
system continues working even if some servers fail.

**Quorum approach:**
- N=3 servers, need majority (2) to agree
- Can tolerate 1 failure
- Prevents split-brain: two groups can't both have majority

## Architecture

```
Client                  Lock Server(s)              Protected Resource
  |                          |                            |
  |---acquire(resource)----->|                            |
  |<-------token=1-----------|                            |
  |                          |                            |
  |---access(resource, token=1)---------------------->|  |
  |<------success----------------------------------------||
  |                          |                            |
  |---release(resource)----->|                            |
  |<-------ok----------------|                            |
```

## Real-World Applications

- **Leader election**: One process acquires a special lock to become leader
- **Database migrations**: Ensure exactly one instance runs the migration
- **Distributed cron**: Ensure scheduled tasks run exactly once across cluster
- **Resource allocation**: Coordinate access to shared resources like file systems
- **Configuration management**: Serialize updates to shared configuration

## Running Examples

### Basic Competition

```bash
python example_basic.py
```

Shows multiple clients competing for the same lock. Demonstrates mutual exclusion.

### Failure Handling

```bash
python example_failure.py
```

Shows what happens when a client crashes while holding a lock. Demonstrates
lease expiration providing fault tolerance.

### Fencing Tokens

```bash
python example_fencing.py
```

Shows how fencing tokens prevent split-brain scenarios where a delayed client
tries to access a resource with a stale lock.

### Replicated Servers

```bash
python example_replicated.py
```

Shows a lock manager with multiple replicated servers using majority voting
for fault tolerance.

## Design Patterns

### Lease Expiration

Instead of explicit heartbeats, clients hold leases that expire. This is
simpler and more robust than heartbeat-based approaches.

### Fencing Tokens

Monotonically increasing tokens provide a total ordering of lock acquisitions.
Resources use tokens to detect and reject stale access attempts.

### Majority Quorums

Requiring majority agreement prevents split-brain. Two minority groups cannot
both claim to hold the lock.

## Production Considerations

Real distributed lock managers need additional features:

- **Watch mechanism**: Notify clients when locks become available
- **Session management**: Heartbeats and automatic cleanup
- **Lock queuing**: Fair ordering of waiting clients
- **Deadlock detection**: Identify and resolve circular lock dependencies
- **Read-write locks**: Multiple readers, single writer
- **Persistent storage**: Survive server restarts
- **Hierarchical locks**: Lock entire subtrees efficiently

## Comparison with Systems

### Apache ZooKeeper
- Uses ZAB (Zookeeper Atomic Broadcast) consensus
- Ephemeral nodes represent locks
- Watches notify on lock release
- Sequential nodes for fair queuing

### etcd
- Uses Raft consensus algorithm
- Lease-based TTL for lock expiration
- Transaction support for complex operations
- Watch API for notifications

### Google Chubby
- Paxos consensus
- Advisory locks (clients cooperate voluntarily)
- Used by BigTable, GFS
- Emphasizes availability over consistency

### Redis Redlock
- No consensus, relies on independent instances
- Controversial: criticized by Martin Kleppmann
- Trades safety for performance
- Suitable for advisory locks only

## Further Reading

- [ZooKeeper Documentation](https://zookeeper.apache.org/)
- [etcd Documentation](https://etcd.io/)
- [Chubby: The lock service for loosely-coupled distributed systems](https://research.google/pubs/pub27897/)
- [How to do distributed locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
- [Is Redlock safe?](http://antirez.com/news/101)
