# Conflict-Free Replicated Data Types

<p class="subtitle" markdown="1">scalable data structures</p>

When multiple people edit an online document simultaneously,
the system ensures everyone eventually sees the same content.
Similarly,
when one person edits a document offline and the reconnects,
their changes are merged into the online version.
Traditional approaches to managing this require locking or complex transformations.
[Conflict-Free Replicated Data Types](g:crdt) (CRDTs),
on the other hand,
are designed so that concurrent updates on different replicas
can always be merged automatically without conflicts,
and all replicas eventually converge to the same state.
Updates are always accepted immediately,
and no locking or consensus protocol is needed.

CRDTs guarantee [strong eventual consistency](g:strong-eventual-consistency),
which means three things:

1.  Eventual delivery: every update reaches every replica eventually.
1.  Convergence: replicas that have received the same updates are in the same state.
1.  No conflicts: concurrent updates can always be merged automatically.

The insight that CRDTs rely on
is that some operations are [commutative](g:commutativity) and [associative](g:associativity).
The first property means that order doesn't matter,
i.e., that A+B = B+A.
The second means that group doesnt' matter,
so (A+B)+C = A+(B+C).
If the merge operation for the data type has these properties,
replicas can receive updates in any order and still converge to the same state.
Some approaches to implementing CRDTs also require operations to be [idempotent](g:idempotence),
which means that the operation can be applied any number of times
with the same cumulative effect
(just as zero can be added to a number over and over).

There are two approaches to building CRDTs.
In a [state-based CRDT](g:state-based-crdt),
replicas send their entire state and merge those states.
State-based CRDTs are simpler to reason about,
but have higher network cost because the entire state must be sent for each operation.
They also require merge operations to be commutative, associate, *and* idempotent.

In contrast,
the replicas in [operation-based CRDTs](g:op-based-crdt) send each other *changes* in state
(sometimes called [deltas](g:delta)).
This reduces the network overhead,
but requires exactly-once delivery of operations.
Those operations must commute,
but needn't be idempotent.
We will implement both approaches to understand the trade-offs.

## Last-Write-Wins Register {: #dxdx-lww}

Let's start with the simplest CRDT:
a [last-write-wins register](g:lww-register).
For values that should be overwritten (like a user's profile name),
we can use timestamps to determine which write wins.

<div data-inc="lwwregister.py" data-filter="inc=lww"></div>

To see how this works,
consider three replicas that randomly choose color values to share with peers:

<div data-inc="ex_lwwregister.py" data-filter="inc=replica"></div>

If we run three replicas for 10 timesteps,
the output is:

<div data-inc="ex_lwwregister.txt"></div>

Chiti's final value is different because all three replicas wrote at time 10:
Ahmed and Baemi set "red", while Chiti set "green".
Since they all have the same timestamp,
the register breaks ties by comparing replica IDs.
If the simulation ran a little longer,
all three copies would converg on "green"
because Chiti > Baemi > Ahmed alphabetically.

An LWW-Register has a weakness:
concurrent writes to the same register result in one being lost
(either the one with the earlier timestamp or with the lower replica ID).
This is acceptable for some use cases (like "last edit wins" in a profile),
but not for others.
The key trade-off is simplicity versus data preservation.
An LWW register never produces a conflict that needs manual resolution,
but it also never preserves both sides of a concurrent update.
This makes it a poor fit for situations where losing a write is costly,
such as a shared to-do list where two people add items at the same time.

## Counters {: #crdt-counter}

Another CRDT is a [grow-only counter](g:grow-only-counter)
whose value can only increase.
Each replica maintains a vector of counters, one per replica:

<div data-inc="gcounter.py" data-filter="inc=gcounter"></div>

The G-Counter works by having each replica only modify its own entry in the vector.
When merging,
we take the maximum of each entry.
This operation is commutative, associative, and idempotent,
which guarantees convergence.

A G-Counter solves the problem of counting across multiple replicas that can't always communicate.
Imagine three servers tracking how many times a button has been clicked.
Users hit whichever server is nearest, and the servers sync up when they can.
A naive approach is to have each server keep a single integer and share its value with the other two,
but this breaks because there's no way to tell whether a value Ahmed receives from Baemi
already includes Ahmed's updates or not.

In a G-Counter,
each replica only increments its own entry:
for example,
Ahmed's server only ever touches `counts["Ahmed"]`.
This ensures that there's never a conflict because no two replicas write to the same slot.
When replicas sync,
they can safely take the `max` of each slot,
because a higher value always means that replica has done more increments.
`max` is idempotent (applying the same sync twice is harmless),
commutative (order doesn't matter),
and associative (grouping doesn't matter),
which makes it suitable for a CRDT.

It's important to note that the overall value of the G-Counter is the sum of the individual values,
not their maximum or any single local value.
Again,
each slot tracks how many increments that specific replica has performed,
so the total is how many increments have happened across all replicas.

To make it concrete, consider this output:

```txt
Ahmed: value=5, counts={'Ahmed': 3, 'Baemi': 2}
Baemi: value=5, counts={'Baemi': 3, 'Ahmed': 2}
Chiti: value=7, counts={'Chiti': 3, 'Ahmed': 2, 'Baemi': 2}
```

Ahmed and Baemi have synced with each other,
so they agree,
but neither has synced recently with Chiti.
Chiti has synced with them, though,
so Chiti's view is more complete.
Once all three sync,
they'll all converge to:

```txt
counts={'Ahmed': 3, 'Baemi': 3, 'Chiti': 3}`
```

with the value 9.
No increments are lost, regardless of sync order or timing.

A grow-only counter is limited.
What if we want to be able to decrement the value?
A [positive-negative counter](g:pn-counter), or PN-Counter, uses two G-Counters:
one for increments, one for decrements.
This works because increments and decrements are tracked separately.
Each remains monotonically increasing, so the G-Counter merge properties still apply.

<div data-inc="pncounter.py" data-filter="inc=pncounter"></div>

## Observed-Remove Set (OR-Set) {: #crdt-orset}

Sets are trickier to implement than counters.
If Ahmed adds X and Baemi removes X concurrently, should X be in the final set?

The OR-Set uses unique tags to track which adds have been observed by which removes.
The key idea is that an element is in the set if there is an add tag that hasn't been removed.
This gives "add-wins" semantics:
concurrent add and remove operations result in the element being present.

<div data-inc="orset.py" data-filter="inc=orset"></div>

This example shows an OR-set in operation:

<div data-inc="ex_orset.py" data-filter="inc=replica"></div>
<div data-inc="ex_orset.txt"></div>

## Operation-Based CRDTs {: #crdt-op}

While state-based CRDTs send the full state between replicas
operation-based CRDTs send just the operations.
Let's implement an operation-based counter
by defining a dataclass to represent a single operation:

<div data-inc="opbased_counter.py" data-filter="inc=op"></div>

and then a class to use it:

<div data-inc="opbased_counter.py" data-filter="inc=counter"></div>

Operation-based CRDTs require reliable broadcast
to ensure that every operation reaches every replica exactly once.
In practice,
this means tracking which operations have been delivered and handling duplicates,
which is what the `applied_ops` member of the `OpBasedCounter` class above does.

The `Replica` class below exercises this counter:

<div data-inc="ex_opbased_counter.py" data-filter="inc=replica"></div>

Unlike the state-based examples that sync by merging full state,
each replica creates an increment or decrement operation with a unique ID,
applies it locally,
and then broadcasts it to all the other replicates.
The replica then drains its inbox and applies received operations,
skipping duplicates via `op_id`.
As the output below shows,
all replicas converge to the same value
because every operation is delivered to every replica exactly once:

<div data-inc="ex_opbased_counter.txt"></div>

## Network Partition Simulation {: #crdt-partition}

A [network partition](g:network-partition) happens
when nodes in a distributed system temporarily can't communicate,
which causes them to form isolated groups.
As a result,
messages sent from one part of the system may not reach another,
effectively splitting the system into disconnected segments.

One of CRDTs' key benefits is [partition tolerance](g:partition-tolerance).
Let's simulate a network partition using the `GCounter` class defined earlier.
First,
we create a simple dataclass to represent peers in the network:

<div data-inc="ex_partition.py" data-filter="inc=peer"></div>

Next,
we define a `Replica` process that repeatedly tries to synchronize
with a randomly-selected peer:

<div data-inc="ex_partition.py" data-filter="inc=replica"></div>

We then create a partition controller that creates and heals a partition:

<div data-inc="ex_partition.py" data-filter="inc=partition"></div>

Finally,
we create three replicas and force a break in the network
at a particular time and for a particular duration:

<div data-inc="ex_partition.py" data-filter="inc=sim"></div>

As the output shows,
the counter recovers from the partitioning:

<div data-inc="ex_partition.txt"></div>

## Exercises {: #crdt-exercises}

FIXME: add exercises.
