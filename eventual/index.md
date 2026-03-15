# Eventually Consistent Key-Value Store

The [CAP theorem][cap-theorem] says that when network partitions occur,
systems must choose between consistency (all nodes see the same data)
and availability (the system continues to respond).
Traditional databases choose consistency:
they stop accepting writes during a partition to avoid conflicts.
But for many applications,
availability is more valuable than immediate consistency.

[DynamoDB][dynamodb],
[Apache Cassandra][apache-cassandra],
and [Riak][riak] therefore take a different approach:
they remain available during partitions and accept that replicas might temporarily disagree.
They use techniques like vector clocks to track causality
and quorum protocols to balance consistency and availability.

This chapter builds a simplified eventually consistent key-value store to demonstrate these concepts.
It shows how systems handle concurrent writes,
detect conflicts using vector clocks,
and use read repair to synchronize replicas.

## The CAP Theorem in Practice {: #eventual-cap}

Imagine a key-value store with three replicas of each key:

1.  Client A writes "X = 1" to replicas 1 and 2.
1.  A network partition separates replica 3.
1.  Client B writes "X = 2" to replicas 2 and 3.
1.  The partition heals.

What is the value of X?
Replica 1 has "X = 1", replica 2 saw both writes, and replica 3 has "X = 2",
so there is a conflict.
Traditional databases would have prevented this by requiring all replicas to agree before accepting a write,
But that makes the system unavailable during the partition.

Our system accepts both writes and uses version vectors to track that X has two concurrent versions.
When a client reads X,
we can either return both versions and let the application decide how to resolve the conflict,
or use a simple rule like "last write wins" based on timestamps.

## Vector Clocks for Causality {: #eventual-clock}

Vector clocks let us determine if two events are causally related or concurrent.
Each replica maintains a counter for every replica in the system:

<div data-inc="vector_clock.py" data-filter="inc=vectorclock"></div>

In our implementation,
the vector clock is a dictionary mapping replica IDs to integers.
When a replica performs an operation, it increments its own counter.
When a recplica receives a message with a vector clock,
it takes the maximum of each component with its local clock.
The key insight is that if clock A happens-before clock B,
then A's event causally precedes B's.
If neither happens-before the other,
the events are concurrent.

## Versioned Values {: #eventual-version}

Each value is stored with its vector clock:

<div data-inc="versioned_value.py" data-filter="inc=versionedvalue"></div>

When storing multiple versions of a key,
we keep only the ones that are concurrent (neither happens-before the other).
If a new version happens-after an existing version,
we can discard the old one.

## Storage Node {: #eventual-storage}

Storage nodes can exchange four kinds of messages:

<div data-inc="messages.py" data-filter="inc=messages"></div>

Each storage node maintains a replica of a subset of keys.
The node's constructor sets up its data store and creates the queue it uses to receive requests:

<div data-inc="storage_node.py" data-filter="inc=storage_init"></div>

The `run` method dispatches reads and writes to dedicated handlers.
`_handle_read` returns all stored versions of a key:

<div data-inc="storage_node.py" data-filter="inc=storage_read"></div>

The write handler is where causality is maintained.
It increments the local clock,
merges the client's causal context,
and discards any stored versions superseded by the new value:

<div data-inc="storage_node.py" data-filter="inc=storage_write"></div>

When writing a new version, we:

1.  increment our local clock,
1.  merge the client's context (if provided) to preserve causality,
1.  remove any existing versions that are superseded by the new version, and
1.  keep concurrent versions, creating a conflict.

## Coordinator with Quorum Protocol {: #eventual-coord}

The coordinator manages replication across storage nodes.
It implements quorum reads and writes:
for N replicas,
we wait for R replicas to respond to a read and W replicas to respond to a write.
R + W > N guarantees that we see the latest write.

The constructor takes the list of storage nodes and quorum parameters,
and `_get_replicas` uses consistent hashing to choose which nodes store a given key:

<div data-inc="coordinator.py" data-filter="inc=coord_init"></div>

A read sends requests to R replicas in parallel and merges their responses:

<div data-inc="coordinator.py" data-filter="inc=coord_read"></div>

A write sends the new value to W replicas,
each of which updates its local clock.
The coordinator merges those clocks to return a causal context to the client:

<div data-inc="coordinator.py" data-filter="inc=coord_write"></div>

`_merge_versions` resolves the list of all versions returned by replicas,
discarding any version whose clock is dominated by another:

<div data-inc="coordinator.py" data-filter="inc=coord_merge"></div>

The quorum protocol is the heart of tunable consistency.
With N=3, R=2, W=2:

-   Writes succeed after 2 nodes acknowledge (available even if 1 node is down).
-   Reads query 2 nodes (at least one will have the latest write).
-   R + W = 4 > N = 3, ensuring reads see the latest writes.

## Client Implementation {: #eventual-client}

Clients read values, resolve conflicts, and write back.
The client stores a causal context per key and works through a list of operations:

<div data-inc="kv_client.py" data-filter="inc=kv_init"></div>

When reading, the client checks for conflicts.
If a single version is returned there is no conflict.
If multiple concurrent versions are returned,
the client resolves them using last-write-wins and merges all their clocks:

<div data-inc="kv_client.py" data-filter="inc=kv_read"></div>

When writing,
the client passes its current causal context so that
the coordinator can detect whether the write is concurrent with or follows previous writes:

<div data-inc="kv_client.py" data-filter="inc=kv_write"></div>

The client maintains a context (vector clock) for each key.
When writing, it passes this context to preserve causality.
When reading multiple versions (a conflict),
it resolves using last-write-wins but merges all clocks to capture the complete causality.

## Running a Simulation {: #eventual-sim}

Let's create a scenario showing concurrent writes and conflict resolution:

<div data-inc="ex_basic.py" data-filter="inc=basicexample"></div>
<div data-inc="ex_basic.txt"></div>

Now let's create a more interesting scenario with concurrent conflicting writes:

<div data-inc="ex_conflict.py" data-filter="inc=conflictexample"></div>
<div data-inc="ex_conflict.txt"></div>

## Handling Network Partitions {: #eventual-partition}

Let's simulate a network partition to see how the system maintains availability.
`PartitionedCoordinator` extends the base coordinator with the ability to mark nodes as unreachable:

<div data-inc="partitioned_coordinator.py" data-filter="inc=partition_init"></div>

Reads skip any partitioned nodes.
If fewer than R nodes are available the read fails;
otherwise it proceeds with only the reachable replicas:

<div data-inc="partitioned_coordinator.py" data-filter="inc=partition_read"></div>

Writes follow the same pattern, requiring W reachable replicas before proceeding:

<div data-inc="partitioned_coordinator.py" data-filter="inc=partition_write"></div>

Let's try it out:

<div data-inc="ex_partition.py" data-filter="inc=partitionexample"></div>

## Read Repair {: #eventual-repair}

A real system needs mechanisms to ensure all replicas eventually converge.
Read repair happens during reads:
if we detect replicas are out of sync,
we push the latest version to lagging replicas.
`CoordinatorWithReadRepair` overrides `read` to query all replicas rather than just a quorum
so that it can identify which ones are behind:

<div data-inc="coordinator_with_read_repair.py" data-filter="inc=repair_read"></div>

After collecting all responses,
`_perform_read_repair` compares each replica's set of versions against the merged result
and writes missing versions back to any replica that is out of date:

<div data-inc="coordinator_with_read_repair.py" data-filter="inc=repair_perform"></div>

Read repair ensures that whenever we read a key,
we fix any inconsistencies we discover.
Over time, this brings all replicas into sync.

## Real-World Considerations {: #eventual-real}

Our implementation demonstrates core concepts, but production systems need additional features:

1.  Hinted handoff:
    when a node is temporarily down, writes intended for it are stored on another node with a hint.
    When the node recovers, the hints are replayed.

1.  Gossip protocol:
    nodes exchange information about cluster membership and failure detection through epidemic-style gossip.

1.  Compaction:
    Nodes merge version history periodically to avoid unbounded growth.
