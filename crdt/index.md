# Conflict-Free Replicated Data Types (CRDTs)

When multiple people edit a Google Doc simultaneously, how does the system ensure everyone eventually sees the same content?
When you edit a document offline on your phone and someone else edits it on their laptop, how do the changes merge when you reconnect?
Traditional approaches use locking or operational transformation, but these require coordination and can fail during network partitions.

Conflict-Free Replicated Data Types (CRDTs) solve this problem through mathematics rather than coordination.
CRDTs are data structures designed so that concurrent updates on different replicas can always be merged automatically, without conflicts, and all replicas eventually converge to the same state.
No consensus protocol needed.
No locking required.
Updates are always accepted immediately.

This pattern appears throughout modern distributed systems: Google Docs uses CRDTs for collaborative editing, Figma for real-time design collaboration, Riak for distributed databases, and Redis for geo-replicated caches.
Understanding CRDTs is essential for building partition-tolerant, offline-first applications.

## The CRDT Promise

CRDTs make a powerful guarantee: **Strong Eventual Consistency**.
This means:

1.  **Eventual delivery**: Every update reaches every replica eventually
1.  **Convergence**: Replicas that have received the same updates are in the same state
1.  **No conflicts**: Concurrent updates can always be merged automatically

The key insight is that some operations are **commutative** and **associative**:
- Commutative: A + B = B + A (order doesn't matter)
- Associative: (A + B) + C = A + (B + C) (grouping doesn't matter)

If your merge operation has these properties, replicas can receive updates in any order and still converge to the same state.

## Two Flavors: State-Based vs Operation-Based

There are two main CRDT approaches:

**State-based CRDTs (CvRDTs)**: Replicas send their entire state and merge states
- Simple to reason about
- Higher network overhead (sending full state)
- Merge must be commutative, associative, and idempotent

**Operation-based CRDTs (CmRDTs)**: Replicas send operations (deltas) and apply them
- Lower network overhead (sending just operations)
- Requires exactly-once delivery of operations
- Operations must commute

We'll implement both approaches to understand the trade-offs.

## Grow-Only Counter (G-Counter)

Let's start with the simplest CRDT: a counter that can only increase.
Each replica maintains a vector of counters, one per replica:

```python
@dataclass
class GCounter:
    """Grow-only counter (state-based CRDT)."""
    replica_id: str
    counts: Dict[str, int] = field(default_factory=dict)
    
    def increment(self, amount: int = 1):
        """Increment this replica's counter."""
        current = self.counts.get(self.replica_id, 0)
        self.counts[self.replica_id] = current + amount
    
    def value(self) -> int:
        """Get the total count across all replicas."""
        return sum(self.counts.values())
    
    def merge(self, other: 'GCounter'):
        """Merge another counter's state (take max of each replica)."""
        all_replicas = set(self.counts.keys()) | set(other.counts.keys())
        for replica in all_replicas:
            self.counts[replica] = max(
                self.counts.get(replica, 0),
                other.counts.get(replica, 0)
            )
    
    def copy(self) -> 'GCounter':
        """Create a copy of this counter."""
        return GCounter(
            replica_id=self.replica_id,
            counts=self.counts.copy()
        )
    
    def __str__(self):
        return f"GCounter(id={self.replica_id}, value={self.value()}, counts={self.counts})"
```

The G-Counter works by having each replica only modify its own entry in the vector.
When merging, we take the maximum of each entry—this is commutative, associative, and idempotent, guaranteeing convergence.

## PN-Counter: Positive-Negative Counter

A grow-only counter is limited.
What about decrement?
We use two G-Counters: one for increments, one for decrements:

```python
@dataclass
class PNCounter:
    """Positive-Negative counter supporting increment and decrement."""
    replica_id: str
    increments: GCounter = field(default_factory=lambda: GCounter(""))
    decrements: GCounter = field(default_factory=lambda: GCounter(""))
    
    def __post_init__(self):
        self.increments.replica_id = self.replica_id
        self.decrements.replica_id = self.replica_id
    
    def increment(self, amount: int = 1):
        """Increment the counter."""
        self.increments.increment(amount)
    
    def decrement(self, amount: int = 1):
        """Decrement the counter."""
        self.decrements.increment(amount)
    
    def value(self) -> int:
        """Get the current value (increments - decrements)."""
        return self.increments.value() - self.decrements.value()
    
    def merge(self, other: 'PNCounter'):
        """Merge another counter's state."""
        self.increments.merge(other.increments)
        self.decrements.merge(other.decrements)
    
    def copy(self) -> 'PNCounter':
        """Create a copy of this counter."""
        result = PNCounter(self.replica_id)
        result.increments = self.increments.copy()
        result.decrements = self.decrements.copy()
        return result
    
    def __str__(self):
        return f"PNCounter(id={self.replica_id}, value={self.value()})"
```

This works because increments and decrements are tracked separately.
Each remains monotonically increasing, so the G-Counter merge properties still apply.

## Last-Write-Wins Register (LWW-Register)

For values that should be overwritten (like a user's profile name), we use timestamps to determine which write wins:

```python
@dataclass
class LWWRegister:
    """Last-Write-Wins register (state-based CRDT)."""
    value: any = None
    timestamp: float = 0.0
    replica_id: str = ""
    
    def set(self, value: any, timestamp: float, replica_id: str):
        """Set the value with a timestamp."""
        # Use timestamp to break ties, replica_id for determinism
        if (timestamp > self.timestamp or 
            (timestamp == self.timestamp and replica_id > self.replica_id)):
            self.value = value
            self.timestamp = timestamp
            self.replica_id = replica_id
    
    def merge(self, other: 'LWWRegister'):
        """Merge another register (keep higher timestamp)."""
        if (other.timestamp > self.timestamp or
            (other.timestamp == self.timestamp and 
             other.replica_id > self.replica_id)):
            self.value = other.value
            self.timestamp = other.timestamp
            self.replica_id = other.replica_id
    
    def copy(self) -> 'LWWRegister':
        """Create a copy of this register."""
        return LWWRegister(
            value=self.value,
            timestamp=self.timestamp,
            replica_id=self.replica_id
        )
    
    def __str__(self):
        return f"LWWRegister(value={self.value}, ts={self.timestamp:.2f})"
```

LWW-Register has a weakness: concurrent writes to the same register result in one being lost (the one with the earlier timestamp or lower replica ID).
This is acceptable for some use cases (like "last edit wins" in a profile), but not for others.

## Observed-Remove Set (OR-Set)

Sets are trickier.
If replica A adds element X and replica B removes X concurrently, should X be in the final set?
The OR-Set uses unique tags to track which adds have been observed by which removes:

```python
@dataclass
class ORSet:
    """Observed-Remove Set (state-based CRDT)."""
    replica_id: str
    elements: Dict[any, Set[str]] = field(default_factory=dict)  # element -> set of unique tags
    tag_counter: int = 0
    
    def add(self, element: any) -> str:
        """Add an element with a unique tag."""
        self.tag_counter += 1
        tag = f"{self.replica_id}-{self.tag_counter}"
        
        if element not in self.elements:
            self.elements[element] = set()
        self.elements[element].add(tag)
        
        return tag
    
    def remove(self, element: any):
        """Remove an element (removes all observed tags)."""
        if element in self.elements:
            del self.elements[element]
    
    def contains(self, element: any) -> bool:
        """Check if element is in the set."""
        return element in self.elements and len(self.elements[element]) > 0
    
    def value(self) -> Set[any]:
        """Get the current set of elements."""
        return {elem for elem, tags in self.elements.items() if tags}
    
    def merge(self, other: 'ORSet'):
        """Merge another set's state."""
        # Union of all tags for each element
        all_elements = set(self.elements.keys()) | set(other.elements.keys())
        
        for element in all_elements:
            self_tags = self.elements.get(element, set())
            other_tags = other.elements.get(element, set())
            merged_tags = self_tags | other_tags
            
            if merged_tags:
                self.elements[element] = merged_tags
    
    def copy(self) -> 'ORSet':
        """Create a copy of this set."""
        result = ORSet(self.replica_id)
        result.elements = {k: v.copy() for k, v in self.elements.items()}
        result.tag_counter = self.tag_counter
        return result
    
    def __str__(self):
        return f"ORSet(id={self.replica_id}, value={self.value()})"
```

The OR-Set principle: an element is in the set if there exists an add tag that hasn't been removed.
This gives "add-wins" semantics—concurrent add and remove results in the element being present.

## CRDT Replica with Synchronization

Now let's create replicas that can update their CRDTs and synchronize with each other:

```python
class CRDTReplica(Process):
    """A replica maintaining CRDT state and syncing with others."""
    
    def init(self, replica_id: str, sync_interval: float = 2.0):
        self.replica_id = replica_id
        self.sync_interval = sync_interval
        
        # Initialize CRDTs
        self.counter = PNCounter(replica_id)
        self.register = LWWRegister()
        self.orset = ORSet(replica_id)
        
        # Track other replicas for syncing
        self.other_replicas: List['CRDTReplica'] = []
        
        # Statistics
        self.updates_applied = 0
        self.syncs_sent = 0
    
    async def run(self):
        """Periodically sync with other replicas."""
        while True:
            await self.timeout(self.sync_interval)
            await self.sync_with_peers()
    
    def add_peer(self, replica: 'CRDTReplica'):
        """Register another replica to sync with."""
        if replica not in self.other_replicas:
            self.other_replicas.append(replica)
    
    async def sync_with_peers(self):
        """Send state to all peers."""
        for peer in self.other_replicas:
            await self.send_state_to(peer)
    
    async def send_state_to(self, peer: 'CRDTReplica'):
        """Send our CRDT state to a peer."""
        self.syncs_sent += 1
        
        # Copy our state to send
        counter_copy = self.counter.copy()
        register_copy = self.register.copy()
        set_copy = self.orset.copy()
        
        # Peer receives and merges
        peer.receive_state(counter_copy, register_copy, set_copy, self.replica_id)
    
    def receive_state(self, counter: PNCounter, register: LWWRegister, 
                     orset: ORSet, from_replica: str):
        """Receive and merge state from another replica."""
        self.counter.merge(counter)
        self.register.merge(register)
        self.orset.merge(orset)
        
        print(f"[{self.now:.1f}] {self.replica_id}: Received state from {from_replica}")
        print(f"  Counter: {self.counter.value()}")
        print(f"  Register: {self.register.value}")
        print(f"  Set: {self.orset.value()}")
    
    def local_increment(self, amount: int = 1):
        """Locally increment the counter."""
        self.counter.increment(amount)
        self.updates_applied += 1
        print(f"[{self.now:.1f}] {self.replica_id}: Incremented by {amount} "
              f"-> {self.counter.value()}")
    
    def local_decrement(self, amount: int = 1):
        """Locally decrement the counter."""
        self.counter.decrement(amount)
        self.updates_applied += 1
        print(f"[{self.now:.1f}] {self.replica_id}: Decremented by {amount} "
              f"-> {self.counter.value()}")
    
    def local_set_register(self, value: any):
        """Locally set the register value."""
        self.register.set(value, self.now, self.replica_id)
        self.updates_applied += 1
        print(f"[{self.now:.1f}] {self.replica_id}: Set register to '{value}'")
    
    def local_add_to_set(self, element: any):
        """Locally add element to set."""
        self.orset.add(element)
        self.updates_applied += 1
        print(f"[{self.now:.1f}] {self.replica_id}: Added '{element}' to set "
              f"-> {self.orset.value()}")
    
    def local_remove_from_set(self, element: any):
        """Locally remove element from set."""
        self.orset.remove(element)
        self.updates_applied += 1
        print(f"[{self.now:.1f}] {self.replica_id}: Removed '{element}' from set "
              f"-> {self.orset.value()}")
```

## Simulating Concurrent Updates

Let's create a simulation where replicas make concurrent updates and eventually converge:

```python
class CRDTWorkload(Process):
    """Generate CRDT operations on a replica."""
    
    def init(self, replica: CRDTReplica, operations: List[tuple]):
        self.replica = replica
        self.operations = operations
    
    async def run(self):
        """Execute operations with delays."""
        for op_type, *args in self.operations:
            if op_type == "wait":
                await self.timeout(args[0])
            elif op_type == "increment":
                self.replica.local_increment(args[0] if args else 1)
            elif op_type == "decrement":
                self.replica.local_decrement(args[0] if args else 1)
            elif op_type == "set":
                self.replica.local_set_register(args[0])
            elif op_type == "add":
                self.replica.local_add_to_set(args[0])
            elif op_type == "remove":
                self.replica.local_remove_from_set(args[0])
            
            # Small delay between operations
            await self.timeout(0.1)


def run_basic_simulation():
    """Demonstrate basic CRDT convergence."""
    env = Environment()
    
    # Create three replicas
    replica1 = CRDTReplica(env, "R1", sync_interval=3.0)
    replica2 = CRDTReplica(env, "R2", sync_interval=3.0)
    replica3 = CRDTReplica(env, "R3", sync_interval=3.0)
    
    # Connect replicas in a mesh
    replica1.add_peer(replica2)
    replica1.add_peer(replica3)
    replica2.add_peer(replica1)
    replica2.add_peer(replica3)
    replica3.add_peer(replica1)
    replica3.add_peer(replica2)
    
    # Replica 1: increment counter
    workload1 = CRDTWorkload(env, replica1, [
        ("increment", 5),
        ("set", "Alice"),
        ("add", "apple"),
        ("add", "banana"),
    ])
    
    # Replica 2: concurrent operations
    workload2 = CRDTWorkload(env, replica2, [
        ("increment", 3),
        ("set", "Bob"),
        ("add", "cherry"),
    ])
    
    # Replica 3: more concurrent operations
    workload3 = CRDTWorkload(env, replica3, [
        ("decrement", 2),
        ("set", "Charlie"),
        ("add", "banana"),  # Concurrent add of same element
        ("remove", "apple"),  # Concurrent remove
    ])
    
    # Run simulation
    env.run(until=15)
    
    # Check convergence
    print("\n=== Final States ===")
    print(f"R1: Counter={replica1.counter.value()}, "
          f"Register='{replica1.register.value}', "
          f"Set={replica1.orset.value()}")
    print(f"R2: Counter={replica2.counter.value()}, "
          f"Register='{replica2.register.value}', "
          f"Set={replica2.orset.value()}")
    print(f"R3: Counter={replica3.counter.value()}, "
          f"Register='{replica3.register.value}', "
          f"Set={replica3.orset.value()}")
    
    # Verify convergence
    assert replica1.counter.value() == replica2.counter.value() == replica3.counter.value()
    assert replica1.register.value == replica2.register.value == replica3.register.value
    assert replica1.orset.value() == replica2.orset.value() == replica3.orset.value()
    
    print("\n✓ All replicas converged!")


if __name__ == "__main__":
    run_basic_simulation()
```

## Operation-Based CRDTs

State-based CRDTs send full state.
Operation-based CRDTs send just the operations.
Let's implement an operation-based counter:

```python
@dataclass
class Operation:
    """An operation on a CRDT."""
    op_type: str
    replica_id: str
    amount: int = 0
    element: any = None
    timestamp: float = 0.0
    tag: str = ""


class OpBasedCounter:
    """Operation-based PN-Counter."""
    
    def __init__(self, replica_id: str):
        self.replica_id = replica_id
        self.value = 0
        self.applied_ops: Set[str] = set()  # For deduplication
    
    def increment(self, amount: int = 1) -> Operation:
        """Create increment operation."""
        return Operation(
            op_type="increment",
            replica_id=self.replica_id,
            amount=amount
        )
    
    def decrement(self, amount: int = 1) -> Operation:
        """Create decrement operation."""
        return Operation(
            op_type="decrement",
            replica_id=self.replica_id,
            amount=amount
        )
    
    def apply(self, op: Operation, op_id: str):
        """Apply an operation if not already applied."""
        if op_id in self.applied_ops:
            return  # Already applied, skip (idempotence)
        
        self.applied_ops.add(op_id)
        
        if op.op_type == "increment":
            self.value += op.amount
        elif op.op_type == "decrement":
            self.value -= op.amount
    
    def __str__(self):
        return f"OpCounter(id={self.replica_id}, value={self.value})"
```

Operation-based CRDTs require reliable broadcast (every operation reaches every replica exactly once).
In practice, this means tracking which operations have been delivered and handling duplicates.

## Network Partition Simulation

One of CRDTs' key benefits is partition tolerance.
Let's simulate a network partition:

```python
class PartitionedCRDTReplica(CRDTReplica):
    """CRDT replica that can be partitioned."""
    
    def init(self, replica_id: str, sync_interval: float = 2.0):
        super().init(replica_id, sync_interval)
        self.partitioned_from: Set[str] = set()
    
    def partition_from(self, replica_id: str):
        """Simulate network partition from another replica."""
        self.partitioned_from.add(replica_id)
        print(f"[{self.now:.1f}] {self.replica_id}: Partitioned from {replica_id}")
    
    def heal_partition(self, replica_id: str):
        """Heal network partition."""
        self.partitioned_from.discard(replica_id)
        print(f"[{self.now:.1f}] {self.replica_id}: Healed partition with {replica_id}")
    
    async def send_state_to(self, peer: 'CRDTReplica'):
        """Send state only if not partitioned."""
        if peer.replica_id in self.partitioned_from:
            return  # Network partition, can't send
        
        await super().send_state_to(peer)


class PartitionManager(Process):
    """Manages network partitions."""
    
    def init(self, replicas: List[PartitionedCRDTReplica]):
        self.replicas = replicas
    
    async def run(self):
        """Create and heal partitions."""
        # Create partition at time 2
        await self.timeout(2.0)
        self.replicas[0].partition_from(self.replicas[1].replica_id)
        self.replicas[1].partition_from(self.replicas[0].replica_id)
        
        # Heal partition at time 8
        await self.timeout(6.0)
        self.replicas[0].heal_partition(self.replicas[1].replica_id)
        self.replicas[1].heal_partition(self.replicas[0].replica_id)


def run_partition_simulation():
    """Demonstrate CRDT behavior during network partition."""
    env = Environment()
    
    # Create two replicas
    replica1 = PartitionedCRDTReplica(env, "R1", sync_interval=1.0)
    replica2 = PartitionedCRDTReplica(env, "R2", sync_interval=1.0)
    
    replica1.add_peer(replica2)
    replica2.add_peer(replica1)
    
    # Create partition manager
    partition_mgr = PartitionManager(env, [replica1, replica2])
    
    # Workload: updates during partition
    workload1 = CRDTWorkload(env, replica1, [
        ("wait", 3.0),
        ("increment", 10),
        ("add", "item1"),
        ("set", "R1_value"),
    ])
    
    workload2 = CRDTWorkload(env, replica2, [
        ("wait", 3.0),
        ("increment", 5),
        ("add", "item2"),
        ("set", "R2_value"),
    ])
    
    # Run simulation
    env.run(until=15)
    
    print("\n=== Final State After Partition Heal ===")
    print(f"R1: Counter={replica1.counter.value()}, "
          f"Register='{replica1.register.value}', "
          f"Set={replica1.orset.value()}")
    print(f"R2: Counter={replica2.counter.value()}, "
          f"Register='{replica2.register.value}', "
          f"Set={replica2.orset.value()}")
    
    print("\n✓ CRDTs converged despite partition!")


if __name__ == "__main__":
    run_partition_simulation()
```

## Real-World Considerations

Our implementation demonstrates core concepts, but production CRDT systems need:

**Garbage collection**: CRDT metadata grows over time.
Systems need to compact tombstones, merge tags, and remove obsolete version vectors.

**Delta-state CRDTs**: Instead of sending full state, send only recent changes (deltas).
This reduces network overhead while maintaining state-based CRDT properties.

**Causal delivery**: Operation-based CRDTs require operations to be delivered in causal order (if op1 happened-before op2, deliver op1 first).

**Compression**: Vector clocks and OR-Set tags can be compressed.
Riak uses version vectors with server-side compaction.

**Semantic awareness**: Generic CRDTs may not match application semantics.
Custom CRDTs can provide better behavior (e.g., shopping cart CRDT that merges intelligently).

**Performance**: State-based CRDTs can have large state; operation-based CRDTs require careful broadcast protocols.
Hybrid approaches exist.

## CRDT Types Comparison

| CRDT | Operations | Use Case | Metadata Overhead |
|------|-----------|----------|-------------------|
| G-Counter | Increment | Metrics, likes | O(replicas) |
| PN-Counter | Inc/Dec | Distributed counters | O(replicas) |
| LWW-Register | Set | Profile fields | O(1) |
| OR-Set | Add/Remove | Shopping cart | O(elements × adds) |
| 2P-Set | Add/Remove (no re-add) | Set semantics | O(elements) |
| RGA | Insert/Delete | Text editing | O(characters) |
| LSeq | Insert/Delete | Collaborative text | O(log n) |

## Conclusion

CRDTs achieve strong eventual consistency without coordination.
The key principles are:

1.  **Commutativity**: Operations can be applied in any order
1.  **Associativity**: Grouping doesn't matter
1.  **Idempotence**: Applying the same operation multiple times has the same effect as once

These properties guarantee that replicas receiving the same updates converge to the same state, regardless of network delays, partitions, or message reordering.

CRDTs trade coordination for metadata.
Instead of coordinating during updates (locks, consensus), we carry extra information (version vectors, unique tags) and use mathematical merge rules.
This makes CRDTs perfect for:

- **Collaborative editing**: Google Docs, Figma
- **Offline-first apps**: Mobile apps that sync when connected
- **Geo-distributed databases**: Riak, Redis
- **Edge computing**: Low-latency updates without cross-datacenter coordination

The simulation approach lets us experiment with concurrent updates, network partitions, and convergence—making CRDT behavior concrete before tackling production implementations.
