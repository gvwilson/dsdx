# Distributed Lock Manager

Multiple processes running on different machines often need to coordinate access to shared resources.
For example,
when a database migration runs,
we want exactly one instance to execute it:
not zero, and not two.
Similarly,
when multiple workers process jobs from a queue,
each job should be handled by exactly one worker.

These coordination problems all require [%g mutual-exclusion "mutual exclusion" %]:
ensuring that only one process holds a lock at any given time.
This is straightforward on a single machine,
since operating systems provide [%g mutex "mutexes" %] and [%g semaphore "semaphores" %].
But a distributed system does not have shared memory,
processes can fail independently,
network messages can be delayed or lost,
and clocks on different machines can drift apart.

Systems like [Apache ZooKeeper][apache-zookeeper],
[etcd][etcd],
and Google's [Chubby][chubby] provide distributed locking as a service.
These systems use consensus algorithms like [Raft][raft] or [Paxos][paxos]
to maintain consistent state across multiple servers, even when some servers fail.
[Redis][redis] implements distributed locks through the [Redlock][redlock] algorithm.
[CockroachDB][cockroachdb] uses distributed locks internally to coordinate schema changes across nodes.

This chapter builds a distributed lock manager that demonstrates
the key concepts in these systems:
lease-based locks with expiration,
fencing tokens to prevent split-brain scenarios,
and a simplified consensus protocol
to ensure lock state remains consistent across multiple lock servers.

## The Split-Brain Scenario {: #distlock-split}

Consider this scenario:

1.  Process A acquires a lock on resource X.
1.  Process A pauses due to garbage collection or a network partition.
1.  The lock manager thinks A has died and grants the lock to Process B.
1.  Process A wakes up, still believing it holds the lock.
1.  Both A and B now access the resource, violating mutual exclusion.

This is called a [%g split-brain "split-brain scenario" %].
To prevent it,
we'll build a distributed lock manager with three main components:

1.  Lock servers that maintain lock state and coordinate through consensus.
1.  Clients that acquire and release locks.
1.  [%g fencing-token "Fencing tokens" %] that prevent stale lock holders from accessing resources.

Our system will use [%g lease-based-lock "lease-based locks" %]:
when a client acquires a lock, it receives a [%g lease "lease" %] that expires after a timeout.
The client must periodically renew the lease to keep the lock.
If it fails or becomes partitioned,
its lease expires and the lock becomes available.

Each lock acquisition receives a monotonically increasing fencing token.
If a resource gets a request with an old token,
it rejects the request.
This prevents a process with a stale lock from corrupting the resource.

## Basic Lock Server {: #distlock-server}

Let's start with a single lock server that manages locks for multiple resources:

[%inc basic_lock_server.py mark=lockclasses %]

`LockServer` and its constructor set up the request queue and a dictionary of per-resource lock states.
Its `run` loop dispatches each incoming request by operation type:

[%inc basic_lock_server.py mark=server_init %]

When a client tries to acquire a lock,
the server first checks whether the current lease has expired,
then grants the lock or renews it if the same client is asking again:

[%inc basic_lock_server.py mark=handle_acquire %]

Releasing a lock simply clears the holder if the request comes from the current holder:

[%inc basic_lock_server.py mark=handle_release %]

## Lock Clients {: #distlock-client}

Clients acquire locks,
do work in [%g critical-section "critical sections" %],
and release locks.
The client class's constructor stores connection details and tracks the current fencing token:

[%inc lock_client.py mark=client_init %]

Its `run` method schedules repeated attempts to acquire the lock and do work:

[%inc lock_client.py mark=client_run %]

`acquire` sends a request to the lock server and waits for a response:

[%inc lock_client.py mark=client_acquire %]

`release` sends a release request when the client is done with the resource:

[%inc lock_client.py mark=client_release %]

Let's run a simple simulation where multiple clients compete for the same lock:

[%inc ex_basic.py mark=basicexample %]
[%inc ex_basic.out %]

The output shows clients taking turns acquiring the lock.
Mutual exclusion is preserved:
only one client holds the lock at a time.

## Handling Failures with Lease Expiration {: #distlock-expiry}

What happens if a client crashes while holding a lock?
Without lease expiration, the lock would be stuck forever.
Let's create a client that fails on purpose:

[%inc failing_client.py mark=failingclient %]

Now let's see what happens:

[%inc ex_failure.py mark=failureexample %]
[%inc ex_failure.out %]

The failing client crashes at time 1.0 without releasing the lock.
But the lease expires at time 4.0 (1.0 + 3.0),
allowing the second client to acquire the lock.
This demonstrates how lease expiration provides fault tolerance.

## Fencing Tokens {: #distlock-fencing}

Lease expiration solves one problem but introduces another.
Consider this sequence:

1.  Client A acquires lock (token 1) with lease expiring at time 10.
1.  Client A pauses from time 2 to time 12.
1.  At time 10, the lease expires.
1.  Client B acquires lock (token 2) at time 11.
1.  Client A wakes up at time 12, still thinks it has the lock.

If both clients now access the shared resource,
they have violated mutual exclusion.
The solution is fencing tokens.

Here's a protected resource that checks tokens:

[%inc protected_resource.py mark=protectedresource %]

Now let's create a client that uses fencing tokens.
The fenced client stores the token it received when acquiring the lock
and passes it with every resource access:

[%inc fenced_client.py mark=fenced_init %]

Its `run` method follows the same lifecycle as the basic client:

[%inc fenced_client.py mark=fenced_run %]

The acquire step is identical to the basic client but stores the token:

[%inc fenced_client.py mark=fenced_acquire %]

When accessing the resource,
the client passes the fencing token so the resource can reject stale requests:

[%inc fenced_client.py mark=fenced_release %]

Now we can demonstrate split-brain prevention:

[%inc ex_fencing.py mark=fencingexample %]
[%inc ex_fencing.out %]

Here's what happens:

1.  Client1 acquires the lock (token 1) at time 0.
1.  Client1 pauses for 5 ticks.
1.  The lease expires at time 3.
1.  Client2 acquires the lock (token 2) at time 4.
1.  Client2 accesses the resource successfully.
1.  Client1 wakes up at time 5 with stale token 1.
1.  The resource rejects Client1 because it has already seen token 2.

The fencing token prevents Client1 from corrupting the resource despite still believing it holds the lock.

## Replicated Lock Servers {: #distlock-replicate}

A single lock server is a single point of failure.
Real distributed lock managers replicate state across multiple servers.
When implementing full consensus using Raft or Paxos,
a client must get agreement from a majority of servers before considering the lock acquired.

Here's a simplified version with replicated lock servers.
The replicated manager holds references to all lock server replicas and a configurable majority threshold:

[%inc replicated_lock_manager.py mark=replicated_init %]

To acquire a lock, the manager sends requests to all replicas and waits until a majority grant it:

[%inc replicated_lock_manager.py mark=replicated_acquire %]

Releasing a lock sends release requests to all replicas that acknowledged the acquire:

[%inc replicated_lock_manager.py mark=replicated_release %]

This client uses the replicated manager:

[%inc replicated_lock_client.py mark=replicatedclient %]

And here's the whole system in action:

[%inc ex_replicated.py mark=replicatedexample %]
[%inc ex_replicated.out %]

Even if one server fails,
the lock manager can continue operating as long as a majority of servers remain available.

## Real-World Considerations {: #distlock-real}

Our implementations demonstrate the core concepts,
but production distributed lock managers need additional features:

1.  Watch mechanism:
    clients can watch for lock release events rather than polling.

1.  Session management:
    clients maintain sessions with heartbeats.
    When a session expires, all locks held by that client are automatically released.

1.  Lock queuing:
    instead of failing when a lock is held,
    clients can queue and be notified when the lock becomes available.

1.  Deadlock detection:
    if Client A holds Lock 1 and waits for Lock 2,
    while Client B holds Lock 2 and waits for Lock 1,
    the system should detect and break the deadlock.

1.  Performance optimization:
    real systems use techniques like read-write locks with multiple readers and a single writer,
    hierarchical locking to lock entire subtrees,
    and lock-free algorithms where possible.
