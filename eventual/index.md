# Eventually Consistent Key-Value Store

Modern distributed systems often face an impossible choice known as the CAP theorem: when network partitions occur, you must choose between consistency (all nodes see the same data) and availability (the system continues to respond).
Traditional databases choose consistency—they stop accepting writes during a partition to avoid conflicts.
But for many applications, availability is more valuable than immediate consistency.

Amazon's DynamoDB, Apache Cassandra, and Riak take a different approach: they remain available during partitions and accept that replicas might temporarily disagree.
They use techniques like vector clocks to track causality, quorum protocols to balance consistency and availability, and anti-entropy mechanisms to eventually converge all replicas to the same state.

This chapter builds a simplified eventually consistent key-value store that demonstrates these core concepts.
You'll see how the system handles concurrent writes, detects conflicts using vector clocks, and uses read repair to synchronize replicas.
We'll implement tunable consistency with quorum reads and writes, and show how the gossip protocol spreads knowledge of failures throughout the cluster.

## The CAP Theorem in Practice

Before we dive into code, let's understand what we're building.
Imagine a key-value store with three replicas of each key:

1.  Client A writes "X = 1" to replicas {1, 2}
1.  Network partition separates replica 3
1.  Client B writes "X = 2" to replicas {2, 3}
1.  Partition heals
1.  What is the value of X?

Replica 1 has "X = 1", replica 2 saw both writes, replica 3 has "X = 2".
We have a conflict.
Traditional databases would have prevented this by requiring all replicas to agree before accepting a write.
But that makes the system unavailable during the partition.

Our system accepts both writes and uses version vectors to track that X has two concurrent versions.
When a client reads X, we return both versions and let the application decide how to resolve the conflict—or we use a simple rule like "last write wins" based on timestamps.

## Vector Clocks for Causality

Vector clocks let us determine if two events are causally related or concurrent.
Each replica maintains a counter for every replica in the system:

```python
from asimpy import Environment, Process, Queue, FirstOf
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
import random


@dataclass
class VectorClock:
    """Vector clock for tracking causality."""
    clocks: Dict[str, int] = field(default_factory=dict)
    
    def increment(self, replica_id: str):
        """Increment the clock for a replica."""
        self.clocks[replica_id] = self.clocks.get(replica_id, 0) + 1
    
    def merge(self, other: 'VectorClock'):
        """Merge with another vector clock (take max of each component)."""
        all_replicas = set(self.clocks.keys()) | set(other.clocks.keys())
        for replica in all_replicas:
            self.clocks[replica] = max(
                self.clocks.get(replica, 0),
                other.clocks.get(replica, 0)
            )
    
    def happens_before(self, other: 'VectorClock') -> bool:
        """Check if this clock happens before another."""
        # self <= other and self != other
        all_replicas = set(self.clocks.keys()) | set(other.clocks.keys())
        
        at_least_one_less = False
        for replica in all_replicas:
            self_val = self.clocks.get(replica, 0)
            other_val = other.clocks.get(replica, 0)
            
            if self_val > other_val:
                return False
            if self_val < other_val:
                at_least_one_less = True
        
        return at_least_one_less
    
    def concurrent_with(self, other: 'VectorClock') -> bool:
        """Check if this clock is concurrent with another."""
        return not self.happens_before(other) and not other.happens_before(self)
    
    def copy(self) -> 'VectorClock':
        """Create a copy of this vector clock."""
        return VectorClock(clocks=self.clocks.copy())
    
    def __str__(self):
        items = sorted(self.clocks.items())
        return "{" + ", ".join(f"{k}:{v}" for k, v in items) + "}"
```

A vector clock is a dictionary mapping replica IDs to integers.
When replica R performs an operation, it increments its own counter.
When receiving a message with a vector clock, a replica merges it (takes the maximum of each component) with its local clock.

The key insight: if clock A happens-before clock B, then A's event causally precedes B's.
If neither happens-before the other, the events are concurrent.

## Versioned Values

Each value is stored with its vector clock:

```python
@dataclass
class VersionedValue:
    """A value with its vector clock."""
    value: Any
    clock: VectorClock
    timestamp: float  # For last-write-wins conflict resolution
    
    def __str__(self):
        return f"Value({self.value}, {self.clock})"
```

When storing multiple versions of a key, we keep only the ones that are concurrent (neither happens-before the other).
If a new version happens-after an existing version, we can discard the old one.

## Storage Node

Each storage node maintains a replica of a subset of keys:

```python
@dataclass
class ReadRequest:
    """Request to read a key."""
    key: str
    client_id: str
    response_queue: Queue


@dataclass
class WriteRequest:
    """Request to write a key."""
    key: str
    value: Any
    context: Optional[VectorClock]  # Client's version context
    client_id: str
    response_queue: Queue


@dataclass
class ReadResponse:
    """Response to a read request."""
    key: str
    versions: List[VersionedValue]  # May have multiple concurrent versions


@dataclass
class WriteResponse:
    """Response to a write request."""
    key: str
    success: bool
    clock: VectorClock


class StorageNode(Process):
    """A storage node that maintains replicas of keys."""
    
    def init(self, node_id: str):
        self.node_id = node_id
        self.request_queue = Queue(self._env)
        # Key -> list of concurrent versioned values
        self.data: Dict[str, List[VersionedValue]] = defaultdict(list)
        self.clock = VectorClock()
        
    async def run(self):
        """Process read and write requests."""
        while True:
            request = await self.request_queue.get()
            
            if isinstance(request, ReadRequest):
                response = self._handle_read(request)
                await request.response_queue.put(response)
            elif isinstance(request, WriteRequest):
                response = self._handle_write(request)
                await request.response_queue.put(response)
    
    def _handle_read(self, request: ReadRequest) -> ReadResponse:
        """Read all concurrent versions of a key."""
        versions = self.data.get(request.key, [])
        
        print(f"[{self.now:.1f}] {self.node_id}: Read {request.key} -> "
              f"{len(versions)} version(s)")
        
        return ReadResponse(key=request.key, versions=versions.copy())
    
    def _handle_write(self, request: WriteRequest) -> WriteResponse:
        """Write a value, handling concurrent versions."""
        # Increment our clock
        self.clock.increment(self.node_id)
        
        # If client provided context, merge it
        new_clock = self.clock.copy()
        if request.context:
            new_clock.merge(request.context)
            new_clock.increment(self.node_id)
        
        # Create new versioned value
        new_version = VersionedValue(
            value=request.value,
            clock=new_clock,
            timestamp=self.now
        )
        
        # Remove versions that this new version supersedes
        existing = self.data[request.key]
        new_versions = []
        
        for version in existing:
            # Keep version if it's concurrent with new version
            if version.clock.concurrent_with(new_clock):
                new_versions.append(version)
            elif new_clock.happens_before(version.clock):
                # The existing version supersedes the new one
                # (shouldn't happen with proper client context)
                new_versions.append(version)
        
        # Add the new version
        new_versions.append(new_version)
        self.data[request.key] = new_versions
        
        print(f"[{self.now:.1f}] {self.node_id}: Wrote {request.key} = "
              f"{request.value} with clock {new_clock}")
        
        return WriteResponse(key=request.key, success=True, clock=new_clock)
```

The `_handle_write` method is crucial.
When writing a new version:

1.  We increment our local clock
1.  We merge the client's context (if provided) to preserve causality
1.  We remove any existing versions that are superseded by the new version
1.  We keep concurrent versions, creating a conflict

## Coordinator with Quorum Protocol

The coordinator manages replication across storage nodes.
It implements quorum reads and writes: for N replicas, we wait for R replicas to respond to a read and W replicas to respond to a write, where R + W > N guarantees we see the latest write.

```python
class Coordinator:
    """Coordinates read/write operations across replicas."""
    
    def __init__(self, env: Environment, nodes: List[StorageNode],
                 replication_factor: int = 3,
                 read_quorum: int = 2,
                 write_quorum: int = 2):
        self.env = env
        self.nodes = nodes
        self.replication_factor = replication_factor
        self.read_quorum = read_quorum
        self.write_quorum = write_quorum
        
        # Simple consistent hashing: hash key to determine replicas
        # In production, use proper consistent hashing ring
        
    def _get_replicas(self, key: str) -> List[StorageNode]:
        """Determine which nodes should store this key."""
        # Hash key to starting position, then take N consecutive nodes
        hash_val = hash(key) % len(self.nodes)
        replicas = []
        for i in range(self.replication_factor):
            idx = (hash_val + i) % len(self.nodes)
            replicas.append(self.nodes[idx])
        return replicas
    
    async def read(self, key: str, client_id: str) -> List[VersionedValue]:
        """Read from R replicas and return all versions."""
        replicas = self._get_replicas(key)
        
        # Send read requests to all replicas
        response_queues = []
        for replica in replicas:
            response_queue = Queue(self.env)
            response_queues.append(response_queue)
            
            request = ReadRequest(key, client_id, response_queue)
            await replica.request_queue.put(request)
        
        # Wait for quorum of responses
        responses = []
        for i in range(self.read_quorum):
            response = await response_queues[i].get()
            responses.append(response)
        
        # Merge all versions from all responses
        all_versions = []
        for response in responses:
            all_versions.extend(response.versions)
        
        # Remove duplicates and superseded versions
        merged_versions = self._merge_versions(all_versions)
        
        # Read repair: if we got different versions, update lagging replicas
        if len(responses) < len(replicas):
            # Some replicas didn't respond yet, but we can still do read repair
            pass  # Simplified: skip read repair for now
        
        return merged_versions
    
    async def write(self, key: str, value: Any, context: Optional[VectorClock],
                   client_id: str) -> VectorClock:
        """Write to W replicas."""
        replicas = self._get_replicas(key)
        
        # Send write requests to all replicas
        response_queues = []
        for replica in replicas:
            response_queue = Queue(self.env)
            response_queues.append(response_queue)
            
            request = WriteRequest(key, value, context, client_id, response_queue)
            await replica.request_queue.put(request)
        
        # Wait for quorum of responses
        responses = []
        for i in range(self.write_quorum):
            response = await response_queues[i].get()
            responses.append(response)
        
        # Return the highest clock
        clocks = [r.clock for r in responses]
        merged_clock = clocks[0].copy()
        for clock in clocks[1:]:
            merged_clock.merge(clock)
        
        return merged_clock
    
    def _merge_versions(self, versions: List[VersionedValue]) -> List[VersionedValue]:
        """Merge versions, keeping only concurrent ones."""
        if not versions:
            return []
        
        # Remove duplicates (same clock)
        unique = {}
        for v in versions:
            clock_str = str(v.clock)
            if clock_str not in unique:
                unique[clock_str] = v
        
        versions = list(unique.values())
        
        # Remove superseded versions
        result = []
        for i, v1 in enumerate(versions):
            superseded = False
            for j, v2 in enumerate(versions):
                if i != j and v1.clock.happens_before(v2.clock):
                    superseded = True
                    break
            if not superseded:
                result.append(v1)
        
        return result
```

The quorum protocol is the heart of tunable consistency.
With N=3, R=2, W=2:

- Writes succeed after 2 nodes acknowledge (available even if 1 node is down)
- Reads query 2 nodes (at least one will have the latest write)
- R + W = 4 > N = 3, ensuring reads see the latest writes

## Client Implementation

Clients read values, resolve conflicts, and write back:

```python
class KVClient(Process):
    """Client that reads and writes to the key-value store."""
    
    def init(self, client_id: str, coordinator: Coordinator,
             operations: List[Tuple[str, str, Any]]):
        self.client_id = client_id
        self.coordinator = coordinator
        self.operations = operations  # List of (op, key, value) tuples
        self.context: Dict[str, VectorClock] = {}  # Track causality per key
        
    async def run(self):
        """Execute operations."""
        for op, key, value in self.operations:
            if op == "write":
                await self.write(key, value)
                await self.timeout(0.5)  # Small delay between operations
            elif op == "read":
                await self.read(key)
                await self.timeout(0.5)
    
    async def read(self, key: str):
        """Read a key and handle conflicts."""
        versions = await self.coordinator.read(key, self.client_id)
        
        if not versions:
            print(f"[{self.now:.1f}] {self.client_id}: Read {key} -> NOT FOUND")
            return None
        
        if len(versions) == 1:
            # No conflict
            version = versions[0]
            self.context[key] = version.clock.copy()
            print(f"[{self.now:.1f}] {self.client_id}: Read {key} -> "
                  f"{version.value} (clock: {version.clock})")
            return version.value
        else:
            # Conflict: multiple concurrent versions
            print(f"[{self.now:.1f}] {self.client_id}: Read {key} -> "
                  f"CONFLICT: {len(versions)} versions")
            for v in versions:
                print(f"  - {v.value} (clock: {v.clock}, ts: {v.timestamp})")
            
            # Resolve conflict: last-write-wins based on timestamp
            latest = max(versions, key=lambda v: v.timestamp)
            
            # Merge all clocks to preserve causality
            merged_clock = versions[0].clock.copy()
            for v in versions[1:]:
                merged_clock.merge(v.clock)
            
            self.context[key] = merged_clock
            print(f"[{self.now:.1f}] {self.client_id}: Resolved to {latest.value}")
            return latest.value
    
    async def write(self, key: str, value: Any):
        """Write a key with causal context."""
        context = self.context.get(key)
        
        clock = await self.coordinator.write(key, value, context, self.client_id)
        self.context[key] = clock
        
        print(f"[{self.now:.1f}] {self.client_id}: Wrote {key} = {value}")
```

The client maintains a context (vector clock) for each key.
When writing, it passes this context to preserve causality.
When reading multiple versions (a conflict), it resolves using last-write-wins but merges all clocks to capture the complete causality.

## Running a Simulation

Let's create a scenario showing concurrent writes and conflict resolution:

```python
def run_basic_simulation():
    """Demonstrate basic operations and conflict resolution."""
    env = Environment()
    
    # Create 3 storage nodes
    nodes = [
        StorageNode(env, "Node1"),
        StorageNode(env, "Node2"),
        StorageNode(env, "Node3")
    ]
    
    # Create coordinator with R=2, W=2, N=3
    coordinator = Coordinator(env, nodes,
                            replication_factor=3,
                            read_quorum=2,
                            write_quorum=2)
    
    # Client 1: writes X=1, then X=2
    client1 = KVClient(env, "Client1", coordinator, [
        ("write", "X", 1),
        ("write", "X", 2),
    ])
    
    # Client 2: reads X after a delay
    async def delayed_client():
        await env.timeout(3.0)
        KVClient(env, "Client2", coordinator, [
            ("read", "X", None),
        ])
    
    env.process(delayed_client())
    env.run(until=10)


if __name__ == "__main__":
    run_basic_simulation()
```

Now let's create a more interesting scenario with concurrent conflicting writes:

```python
def run_conflict_simulation():
    """Demonstrate concurrent writes creating conflicts."""
    env = Environment()
    
    # Create 5 storage nodes
    nodes = [StorageNode(env, f"Node{i+1}") for i in range(5)]
    
    # N=3, R=2, W=2
    coordinator = Coordinator(env, nodes,
                            replication_factor=3,
                            read_quorum=2,
                            write_quorum=2)
    
    # Client 1: writes cart=["item1"]
    client1 = KVClient(env, "Client1", coordinator, [
        ("write", "cart", ["item1"]),
        ("read", "cart", None),
    ])
    
    # Client 2: concurrently writes cart=["item2"] 
    # (without seeing client1's write due to timing)
    async def concurrent_client():
        await env.timeout(0.2)  # Slight delay but before client1's read
        KVClient(env, "Client2", coordinator, [
            ("write", "cart", ["item2"]),
        ])
    
    env.process(concurrent_client())
    
    # Client 3: reads the conflicted cart later
    async def reading_client():
        await env.timeout(3.0)
        KVClient(env, "Client3", coordinator, [
            ("read", "cart", None),
            ("write", "cart", ["item1", "item2"]),  # Resolved value
        ])
    
    env.process(reading_client())
    env.run(until=10)
```

## Handling Network Partitions

Let's simulate a network partition to see how the system maintains availability:

```python
class PartitionedCoordinator(Coordinator):
    """Coordinator that can simulate network partitions."""
    
    def __init__(self, env: Environment, nodes: List[StorageNode],
                 replication_factor: int = 3,
                 read_quorum: int = 2,
                 write_quorum: int = 2):
        super().__init__(env, nodes, replication_factor, read_quorum, write_quorum)
        self.partitioned_nodes: Set[str] = set()
    
    def partition_node(self, node_id: str):
        """Simulate network partition for a node."""
        self.partitioned_nodes.add(node_id)
        print(f"[{self.env.now:.1f}] PARTITION: {node_id} is unreachable")
    
    def heal_partition(self, node_id: str):
        """Heal network partition for a node."""
        self.partitioned_nodes.discard(node_id)
        print(f"[{self.env.now:.1f}] HEALED: {node_id} is reachable")
    
    async def read(self, key: str, client_id: str) -> List[VersionedValue]:
        """Read, skipping partitioned nodes."""
        replicas = self._get_replicas(key)
        available_replicas = [
            r for r in replicas 
            if r.node_id not in self.partitioned_nodes
        ]
        
        if len(available_replicas) < self.read_quorum:
            print(f"[{self.env.now:.1f}] Read failed: insufficient replicas")
            return []
        
        # Send to available replicas
        response_queues = []
        for replica in available_replicas[:self.read_quorum]:
            response_queue = Queue(self.env)
            response_queues.append(response_queue)
            
            request = ReadRequest(key, client_id, response_queue)
            await replica.request_queue.put(request)
        
        responses = []
        for queue in response_queues:
            response = await queue.get()
            responses.append(response)
        
        all_versions = []
        for response in responses:
            all_versions.extend(response.versions)
        
        return self._merge_versions(all_versions)
    
    async def write(self, key: str, value: Any, context: Optional[VectorClock],
                   client_id: str) -> Optional[VectorClock]:
        """Write, skipping partitioned nodes."""
        replicas = self._get_replicas(key)
        available_replicas = [
            r for r in replicas 
            if r.node_id not in self.partitioned_nodes
        ]
        
        if len(available_replicas) < self.write_quorum:
            print(f"[{self.env.now:.1f}] Write failed: insufficient replicas")
            return None
        
        # Send to available replicas
        response_queues = []
        for replica in available_replicas[:self.write_quorum]:
            response_queue = Queue(self.env)
            response_queues.append(response_queue)
            
            request = WriteRequest(key, value, context, client_id, response_queue)
            await replica.request_queue.put(request)
        
        responses = []
        for queue in response_queues:
            response = await queue.get()
            responses.append(response)
        
        clocks = [r.clock for r in responses]
        merged_clock = clocks[0].copy()
        for clock in clocks[1:]:
            merged_clock.merge(clock)
        
        return merged_clock


def run_partition_simulation():
    """Demonstrate behavior during network partition."""
    env = Environment()
    
    nodes = [StorageNode(env, f"Node{i+1}") for i in range(5)]
    coordinator = PartitionedCoordinator(env, nodes,
                                        replication_factor=3,
                                        read_quorum=2,
                                        write_quorum=2)
    
    # Initial write
    client1 = KVClient(env, "Client1", coordinator, [
        ("write", "status", "healthy"),
        ("read", "status", None),
    ])
    
    # Cause a partition
    async def create_partition():
        await env.timeout(2.0)
        coordinator.partition_node("Node3")
        
        # Client still succeeds with remaining nodes
        await env.timeout(1.0)
        KVClient(env, "Client2", coordinator, [
            ("write", "status", "degraded"),
            ("read", "status", None),
        ])
        
        # Heal partition
        await env.timeout(2.0)
        coordinator.heal_partition("Node3")
    
    env.process(create_partition())
    env.run(until=10)
```

## Anti-Entropy and Read Repair

In a real system, we need mechanisms to ensure all replicas eventually converge.
Read repair happens during reads: if we detect replicas are out of sync, we push the latest version to lagging replicas.

```python
class CoordinatorWithReadRepair(Coordinator):
    """Coordinator that performs read repair."""
    
    async def read(self, key: str, client_id: str) -> List[VersionedValue]:
        """Read from R replicas and repair inconsistencies."""
        replicas = self._get_replicas(key)
        
        # Send read requests to ALL replicas (not just quorum)
        response_queues = []
        for replica in replicas:
            response_queue = Queue(self.env)
            response_queues.append(response_queue)
            
            request = ReadRequest(key, client_id, response_queue)
            await replica.request_queue.put(request)
        
        # Wait for quorum, but collect all responses for repair
        responses = []
        for i in range(min(self.read_quorum, len(response_queues))):
            response = await response_queues[i].get()
            responses.append(response)
        
        # Collect remaining responses in background for read repair
        remaining_responses = []
        for i in range(self.read_quorum, len(response_queues)):
            try:
                # Non-blocking check if response available
                # In real async, we'd use timeout or try_get
                response = await response_queues[i].get()
                remaining_responses.append(response)
            except:
                pass
        
        all_responses = responses + remaining_responses
        
        # Merge all versions
        all_versions = []
        for response in all_responses:
            all_versions.extend(response.versions)
        
        merged_versions = self._merge_versions(all_versions)
        
        # Read repair: identify replicas that are missing versions
        if len(merged_versions) > 0 and len(all_responses) > 1:
            await self._perform_read_repair(key, merged_versions, replicas, all_responses)
        
        return merged_versions
    
    async def _perform_read_repair(self, key: str, merged_versions: List[VersionedValue],
                                   replicas: List[StorageNode],
                                   responses: List[ReadResponse]):
        """Update lagging replicas."""
        # Determine which replicas need updates
        for i, response in enumerate(responses):
            replica = replicas[i]
            
            # Check if this replica is missing any versions
            replica_clocks = {str(v.clock) for v in response.versions}
            merged_clocks = {str(v.clock) for v in merged_versions}
            
            if replica_clocks != merged_clocks:
                print(f"[{self.env.now:.1f}] READ REPAIR: Updating {replica.node_id} "
                      f"for key {key}")
                
                # Write missing versions to this replica
                for version in merged_versions:
                    if str(version.clock) not in replica_clocks:
                        response_queue = Queue(self.env)
                        request = WriteRequest(
                            key, version.value, version.clock,
                            "read-repair", response_queue
                        )
                        await replica.request_queue.put(request)
                        await response_queue.get()
```

Read repair ensures that whenever we read a key, we fix any inconsistencies we discover.
Over time, this brings all replicas into sync.

## Real-World Considerations

Our implementation demonstrates core concepts, but production systems need additional features:

**Hinted handoff**: When a node is temporarily down, writes intended for it are stored on another node with a hint.
When the node recovers, the hints are replayed.

**Merkle trees**: For anti-entropy, nodes periodically exchange Merkle tree hashes to efficiently identify which keys differ and need synchronization.

**Gossip protocol**: Nodes exchange information about cluster membership and failure detection through epidemic-style gossip.

**Sloppy quorums**: Instead of requiring specific replicas, accept writes from any N healthy nodes.

**Multi-datacenter replication**: Replicate across geographic regions with different consistency guarantees.

**Compaction**: Merge version history periodically to avoid unbounded growth.

## Conclusion

Eventually consistent systems trade immediate consistency for availability and partition tolerance.
The key techniques are:

1.  **Vector clocks** track causality and detect concurrent writes
1.  **Quorum protocols** (R + W > N) balance consistency and availability
1.  **Conflict resolution** handles concurrent writes through application logic or simple rules
1.  **Read repair** and **anti-entropy** ensure replicas eventually converge
1.  **Partitioning** is handled gracefully—the system stays available

These patterns appear throughout distributed systems.
Shopping carts use vector clocks to merge concurrent updates.
Collaborative editing uses CRDTs (a more sophisticated form of conflict-free merging).
Distributed databases use quorums to tune consistency vs. availability.
