# Distributed Lock Manager

In a distributed system,
multiple processes running on different machines often need to coordinate access to shared resources.
When a database migration runs, you want exactly one instance to execute it—not zero, not two.
When multiple workers process jobs from a queue, each job should be handled by exactly one worker.
When services elect a leader to coordinate cluster operations, exactly one service should become the leader.

These coordination problems all require mutual exclusion: ensuring that only one process can hold a lock at any given time.
In a single-machine system, this is straightforward—the operating system provides mutexes and semaphores.
But in a distributed system, there is no shared memory, processes can fail independently, network messages can be delayed or lost, and clocks on different machines drift apart.

Systems like [Apache ZooKeeper][apache-zookeeper],
[etcd][etcd],
and Google's [Chubby][chubby] provide distributed locking as a service.
These systems use consensus algorithms like [Raft][raft] or [Paxos][paxos]
to maintain consistent state across multiple servers, even when some servers fail.
[Redis][redis] implements distributed locks through the [Redlock][redlock] algorithm.
[CockroachDB][cockroachdb] uses distributed locks internally to coordinate schema changes across nodes.

This chapter builds a distributed lock manager that demonstrates the key challenges and techniques:
lease-based locks with expiration,
fencing tokens to prevent split-brain scenarios,
and a simplified consensus protocol to ensure lock state remains consistent across multiple lock servers.

## The Challenge of Distributed Locking

Why is distributed locking so much harder than local locking? Consider this scenario:

1.  Process A acquires a lock on resource X
1.  Process A pauses due to garbage collection (or network partition)
1.  The lock manager thinks A has died and grants the lock to Process B
1.  Process A wakes up, still believing it holds the lock
1.  Both A and B now access the resource, violating mutual exclusion

This is called a split-brain scenario.
We need mechanisms to detect and prevent it.
The key insight is that we cannot rely on timeouts alone—we need explicit coordination between the lock holder and the lock service.

## Our Implementation Strategy

We'll build a distributed lock manager with three main components:

1.  **Lock servers** that maintain lock state and coordinate through consensus
1.  **Clients** that acquire and release locks
1.  **Fencing tokens** that prevent stale lock holders from accessing resources

Our system will use lease-based locks: when a client acquires a lock, it receives a lease that expires after a timeout.
The client must periodically renew the lease to keep the lock.
If the client fails or becomes partitioned, the lease expires and the lock becomes available.

Each lock acquisition receives a monotonically increasing fencing token.
Resources check this token—if they see a request with an older token, they reject it.
This prevents a zombie process with a stale lock from corrupting the resource.

## Basic Lock Server

Let's start with a single lock server that manages locks for multiple resources:

<div data-inc="basic_lock_server.py" data-filter="inc=lockclasses"></div>

The `LockServer` class and its constructor set up the request queue and a dictionary of per-resource lock states.
Its `run` loop dispatches each incoming request by operation type:

<div data-inc="basic_lock_server.py" data-filter="inc=server_init"></div>

When a client tries to acquire a lock, the server first checks whether the current lease has expired, then grants the lock or renews it if the same client is asking again:

<div data-inc="basic_lock_server.py" data-filter="inc=handle_acquire"></div>

Releasing a lock simply clears the holder if the request comes from the current holder:

<div data-inc="basic_lock_server.py" data-filter="inc=handle_release"></div>

## Lock Clients

Clients acquire locks, do work in critical sections, and release locks.
The client class and its constructor store connection details and track the current fencing token:

<div data-inc="lock_client.py" data-filter="inc=client_init"></div>

The `run` method schedules repeated attempts to acquire the lock and do work:

<div data-inc="lock_client.py" data-filter="inc=client_run"></div>

`acquire` sends a request to the lock server and waits for a response:

<div data-inc="lock_client.py" data-filter="inc=client_acquire"></div>

`release` sends a release request when the client is done with the resource:

<div data-inc="lock_client.py" data-filter="inc=client_release"></div>

Let's run a simple simulation where multiple clients compete for the same lock:

<div data-inc="example_basic.py" data-filter="inc=basicexample"></div>

When you run this, you'll see clients taking turns acquiring the lock.
The mutual exclusion property is preserved—only one client holds the lock at a time.

## Handling Failures with Lease Expiration

What happens if a client crashes while holding a lock?
Without lease expiration, the lock would be stuck forever.
Let's create a client that fails:

<div data-inc="failing_client.py" data-filter="inc=failingclient"></div>

Now let's see what happens:

<div data-inc="example_failure.py" data-filter="inc=failureexample"></div>

The failing client crashes at time 1.0 without releasing the lock.
But the lease expires at time 4.0 (1.0 + 3.0), allowing the second client to acquire the lock.
This demonstrates how lease expiration provides fault tolerance.

## Fencing Tokens

Lease expiration solves one problem but introduces another.
Consider this sequence:

1.  Client A acquires lock (token 1) with lease expiring at time 10
1.  Client A pauses (GC, network partition) from time 2 to time 12
1.  At time 10, the lease expires
1.  Client B acquires lock (token 2) at time 10.5
1.  Client A wakes up at time 12, still thinks it has the lock

If both clients now access the shared resource, we've violated mutual exclusion.
The solution is fencing tokens.

Here's a protected resource that checks tokens:

<div data-inc="protected_resource.py" data-filter="inc=protectedresource"></div>

Now let's create a client that uses fencing tokens.
The fenced client stores the token it received when acquiring the lock and passes it with every resource access:

<div data-inc="fenced_client.py" data-filter="inc=fenced_init"></div>

Its `run` method follows the same lifecycle as the basic client:

<div data-inc="fenced_client.py" data-filter="inc=fenced_run"></div>

The acquire step is identical to the basic client but stores the token:

<div data-inc="fenced_client.py" data-filter="inc=fenced_acquire"></div>

When accessing the resource, the client passes the fencing token so the resource can reject stale requests:

<div data-inc="fenced_client.py" data-filter="inc=fenced_release"></div>

Now we can demonstrate split-brain prevention:

<div data-inc="example_fencing.py" data-filter="inc=fencingexample"></div>

Here's what happens:

1.  Client1 acquires the lock (token 1) at time 0
1.  Client1 pauses for 5 seconds
1.  The lease expires at time 3
1.  Client2 acquires the lock (token 2) at time 4
1.  Client2 accesses the resource successfully
1.  Client1 wakes up at time 5 with stale token 1
1.  The resource rejects Client1 because it has already seen token 2

The fencing token prevents Client1 from corrupting the resource despite still believing it holds the lock.

## Replicated Lock Servers

A single lock server is a single point of failure.
Real distributed lock managers replicate state across multiple servers.
When implementing full consensus (Raft or Paxos), a client must get agreement from a majority of servers before considering the lock acquired.

Here's a simplified version with replicated lock servers.
The replicated manager holds references to all lock server replicas and a configurable majority threshold:

<div data-inc="replicated_lock_manager.py" data-filter="inc=replicated_init"></div>

To acquire a lock, the manager sends requests to all replicas and waits until a majority grant it:

<div data-inc="replicated_lock_manager.py" data-filter="inc=replicated_acquire"></div>

Releasing a lock sends release requests to all replicas that acknowledged the acquire:

<div data-inc="replicated_lock_manager.py" data-filter="inc=replicated_release"></div>

A client using the replicated manager:

<div data-inc="replicated_lock_client.py" data-filter="inc=replicatedclient"></div>

<div data-inc="example_replicated.py" data-filter="inc=replicatedexample"></div>

With replication, even if one server fails, the lock manager can continue operating as long as a majority of servers remain available.
This provides fault tolerance.

## Real-World Considerations

Our implementation demonstrates the core concepts, but production distributed lock managers need additional features:

1.  **Watch mechanism**: Clients can watch for lock release events rather than polling.
ZooKeeper provides this through ephemeral nodes and watches.

1.  **Session management**: Clients maintain sessions with heartbeats.
When a session expires, all locks held by that client are automatically released.

1.  **Lock queuing**: Instead of failing when a lock is held, clients can queue and be notified when the lock becomes available.

1.  **Deadlock detection**: If Client A holds Lock 1 and waits for Lock 2, while Client B holds Lock 2 and waits for Lock 1, the system should detect and break the deadlock.

1.  **Performance optimization**: Real systems use techniques like read-write locks (multiple readers, single writer), hierarchical locking (lock entire subtrees), and lock-free algorithms where possible.

## Conclusion

Distributed locking is fundamental to coordination in distributed systems.
The key challenges are:

1.  **Fault tolerance**: Servers and clients can fail independently
1.  **Network unreliability**: Messages can be delayed, lost, or reordered  
1.  **Clock skew**: Different machines have different notions of time
1.  **Split-brain**: Preventing multiple processes from believing they hold the same lock

Our solutions include:

1.  **Lease-based locks** with expiration to handle failures
1.  **Fencing tokens** to prevent stale lock holders from accessing resources
1.  **Consensus protocols** to maintain consistent state across servers
1.  **Majority voting** to tolerate server failures

These techniques appear throughout distributed systems.
Leader election uses the same mechanisms we've seen here—a candidate acquires a special lock, and the fencing token becomes the leader's epoch number.
Distributed databases use locks to coordinate schema migrations.
Cluster managers use locks to ensure only one instance of a service runs.

The [asimpy][asimpy] simulation approach lets us verify these protocols work correctly under various failure scenarios—client crashes, network delays, lease expirations—before deploying them in production where debugging is much harder.