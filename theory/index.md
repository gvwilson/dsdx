# A Bit of Theory

<div class="callout" markdown="1">

-   Explain what the happens-before relation is
    and use it to determine the order of events in a distributed execution.
-   Describe how logical clocks and vector clocks assign timestamps to events
    without relying on synchronized physical clocks.
-   Compare linearizability, sequential consistency, and eventual consistency,
	and give a concrete example that distinguishes them.
-   State the CAP theorem
    and explain why it is an oversimplification of the real trade-offs in distributed systems.

</div>

When you run a program on a single machine,
you can rely on events happening in a definite order
and every part of the program seeing the same data.
If you write a value to a variable,
you can immediately read that value back.
None of these guarantees hold automatically in a distributed system.

## Clocks and Order {: #theory-clock}

[%b Lamport1978 %] is one of the most influential papers in computer science.
Its central insight is that clocks are unreliable in distributed systems.
Two machines might disagree about the time by milliseconds or even seconds,
and there is no way to synchronize them perfectly.
This means we cannot use wall-clock timestamps
to determine which of two events on different machines happened first.

Lamport proposed an alternative.
Instead of asking, "What time did this happen?"
we should ask, "What happened before what?"
He defined a [%g happens-before "happens-before relation" %]:

1.  If event A occurs before event B on the same machine,
    then A happens-before B.

2.  If machine X sends a message and machine Y receives it,
    then the send happens-before the receive.

3.  If A happens-before B and B happens-before C,
    then A happens-before C
    (i.e., the relation is transitive).

Two events are [%g concurrency "concurrent" %] if neither happens-before the other.
This does not mean they occurred at the same instant;
it just means that we cannot put them in order.

To track this relation in practice, Lamport introduced [%g logical-clock "logical clocks" %].
Each machine maintains a counter;
it increments the counter before each event
and includes the counter's value in every message it sends.
When a machine receives a message,
it sets its counter to the maximum of its current value and the value in the message,
then increments it.
This guarantees that if A happens-before B,
then A's timestamp is less than B's.
Note that the converse is not true:
a lower timestamp does not prove that one event happened first.
This means that logical clocks capture a [%g partial-order "partial order" %],
not a [%g total-order "total order" %].

To make this concrete, consider two processes P and Q:

```
P:  event p1 (clock=1)  -->send msg (clock=2)-->
Q:                                            receive msg (clock=3)  -->event q2 (clock=4)
```

P's clock is 2 when it sends; Q takes max(0, 2) + 1 = 3 when it receives.
We can conclude p1 → q2 (because p1 → send → receive → q2),
but if P also had an event p3 with clock=3 at the same real moment as q2's clock=4,
we cannot say p3 → q2 or q2 → p3—they are concurrent, even though their clock values differ.
This is what it means for the order to be partial: some pairs of events simply have no causal relationship.

[%g vector-clock "Vector clocks" %] extend this idea to capture the full happens-before relation.
Instead of a single counter,
each machine maintains a vector with one entry per machine.
A machine increments its own entry for each event
and sends the entire vector with every message.
When a machine receives a message,
it takes the element-wise maximum of its vector and the incoming one.
Two events are concurrent if and only if neither vector is element-wise less than or equal to the other.
The [G-Counter CRDT](@/crdt/) uses exactly this structure:
each replica tracks its own count in a vector,
and merging takes the element-wise maximum.

For example, with three processes A, B, and C starting with clocks [0,0,0]:

```
A writes:  clock = [1,0,0]  -- sends to B
B receives: clock = max([0,0,0],[1,0,0]) + B's increment = [1,1,0]  -- sends to C
C receives: clock = max([0,0,1],[1,1,0]) + C's increment = [1,1,2]
```

(Here C had already done one local event before receiving B's message, so its own slot was 1.)
Now suppose A also did a separate event, bringing its clock to [2,0,0].
Is A's [2,0,0] concurrent with C's [1,1,2]?
Neither [2,0,0] ≤ [1,1,2] element-wise, nor [1,1,2] ≤ [2,0,0] element-wise, so yes: they are concurrent.

## Consistency Models {: #theory-consistency}

In a single-machine program,
reading a variable always returns the most recent value written to it.
This property is called [%g strong-consistency "strong consistency" %],
and is expensive in a distributed system
because it requires all replicas to coordinate on every operation.

At the other end of the spectrum is [%g eventual-consistency "eventual consistency" %],
which only guarantees that if no new updates are made,
all replicas will eventually converge to the same state.
Eventual consistency says nothing about what a replica might return in the meantime:
a read might return a stale value,
a newer value,
or even a value that no single client ever wrote
if partial updates have been merged in some strange way.
Most eventually-consistent systems behave better in practice than this worst case,
but the guarantee is still very weak.

Strong eventual consistency is a middle ground:
replicas that have received the same set of updates
are guaranteed to be in the same state,
regardless of the order in which those updates arrived.
This is the consistency model that [CRDTs](@/crdt/) provide.
No coordination or consensus is needed,
and there are no conflicts to resolve,
because the data structures are designed
to allow concurrent updates to be merged deterministically.

Several other models lie between strong consistency and eventual consistency.
[%g linearizability "Linearizability" %] means that
every operation appears to take effect at some instant between its invocation and its response,
and all operations are consistent with a single global order.
This is both very useful and very expensive,
since it typically requires consensus protocols like [Paxos][paxos] or [Raft][raft].

To make linearizability concrete: if client A writes X=1 and client B immediately reads X,
linearizability guarantees B sees 1 (assuming A's write finished before B's read started).
An eventually-consistent system might return X=0 if B happened to hit a replica that hadn't received the write yet.

[%g sequential-consistency "Sequential consistency" %] is slightly weaker:
operations appear in some total order that respects each machine's local order,
but that order need not correspond to real time.
[%g causal-consistency "Causal consistency" %] lies between its sequential and eventual cousins:
it guarantees that operations related by happens-before are seen in order by everyone,
but concurrent operations may be seen in different orders by different replicas.
This is closely related to Lamport's happens-before relation
and is often the strongest consistency model
that can be achieved without expensive global coordination.

As a concrete example of causal consistency: if you post a message and then post a reply to it,
any other user who sees your reply must also see your original post
(since the reply causally follows the post).
But two users may see your reply and a friend's concurrent post in different orders,
because those two events have no causal relationship.

## The CAP Theorem {: #theory-cap}

[%b Gilbert2002 %] proved that
a distributed system cannot simultaneously provide all three of the following properties:

-   consistency: every read returns the most recent write;
-   availability: every request receives a response; and
-   partition tolerance: the system continues to operate despite network partitions.

Since network partitions are inevitable in any real distributed system,
the theorem effectively forces a choice between consistency and availability.
A [%g cp-system "CP system" %]
(i.e., one that is consistent and partition-tolerant)
will refuse to respond rather than return stale data during a partition.
Traditional relational databases with synchronous replication behave this way:
if a replica cannot reach the primary,
it rejects writes rather than risk inconsistency.

On the other hand,
an [%g ap-system "AP system" %] (i.e., one that is available and partition-tolerant)
will always respond,
but may return stale or divergent data during a partition.
CRDTs are a tool for building AP systems
because each replica can accept writes independently and merge state later.
They  sacrifice strong consistency in exchange for
guaranteed availability and automatic conflict resolution.
Each CRDT encodes a particular conflict-resolution policy into the data structure itself,
so that no external coordination is ever required.
The cost is that the policies are fixed:
an LWW register always discards concurrent writes in favor of the latest timestamp,
and an OR-Set always resolves a concurrent add and remove in favor of the add.
Whether these policies are acceptable depends on the application.

The CAP theorem is sometimes misunderstood as a simple menu of three options.
In practice,
most of the time there is no partition and the system can be both consistent and available.
The question is what happens during the (hopefully brief) periods when partitions occur.
Modern systems often provide tunable consistency:
a database might allow you to choose strong consistency for financial transactions
and eventual consistency for analytics queries.

The CAP theorem has also been criticized as an oversimplification.
The [%g pacelc "PACELC model" %] extends it:
even when there is no partition (the "else" case),
systems must still trade off latency against consistency.
A linearizable system that avoids partitions still adds latency to every operation
because replicas must coordinate before responding.
This latency–consistency trade-off is often more relevant day-to-day
than the partition–availability trade-off that CAP focuses on.

<section class="exercises" markdown="1">
## Exercises {: #theory-exercises}

1.  Consider three processes P, Q, and R.
    P sends a message to Q; Q processes it and sends a message to R.
    P also sends a separate message directly to R.
    Draw the happens-before relationships between all events.
    Which pairs of events are concurrent?

2.  Suppose a system offers causal consistency.
    You write a blog post (event A),
    then write a comment on it (event B).
    Your friend reads your comment but not the post.
    Does causal consistency allow this?
    What about eventual consistency?
    What about linearizability?

3.  A database has three replicas.
    You configure it with strong consistency for writes (all three must acknowledge)
    and eventual consistency for reads (any one replica may respond).
    Describe a scenario where a client reads a stale value.
    Is this a violation of strong consistency?

4.  Trace the vector clocks for this scenario:
    Write each process's vector clock after each event.
    Which events are concurrent with c1?
    - Process A does two local events (a1, a2), then sends a message to B.
    - Process B does one local event (b1) before receiving A's message, then does b2 after.
    - Process C does one local event (c1) concurrently with everything above.

5.  The OR-Set (covered in the [CRDTs](@/crdt/) lesson) uses "add-wins" semantics.
    Name two other data types where "last-write-wins" semantics would be more appropriate
    and two where "add-wins" would be more appropriate.
    Justify your choices in terms of the consistency model each implies.

</section>
