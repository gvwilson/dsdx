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

```python
from asimpy import Environment, Process, Queue, Timeout
from dataclasses import dataclass
from typing import Dict, Optional
import random


@dataclass
class LockRequest:
    """Request to acquire or release a lock."""
    client_id: str
    resource: str
    operation: str  # "acquire" or "release"
    response_queue: Queue


@dataclass
class LockResponse:
    """Response to a lock request."""
    success: bool
    token: Optional[int] = None
    message: str = ""


@dataclass 
class LockState:
    """State of a single lock."""
    holder: Optional[str] = None
    token: int = 0
    lease_expiry: float = 0
    waiters: list = None
    
    def __post_init__(self):
        if self.waiters is None:
            self.waiters = []
```

The `LockServer` maintains state for each resource and processes lock requests:

```python
class LockServer(Process):
    """A single lock server managing multiple resources."""
    
    def init(self, name: str, lease_duration: float = 5.0):
        self.name = name
        self.lease_duration = lease_duration
        self.request_queue = Queue(self._env)
        self.locks: Dict[str, LockState] = {}
        self.next_token = 1
        
    async def run(self):
        """Process lock requests."""
        while True:
            request = await self.request_queue.get()
            
            if request.operation == "acquire":
                response = await self._handle_acquire(request)
            elif request.operation == "release":
                response = await self._handle_release(request)
            else:
                response = LockResponse(False, message="Unknown operation")
            
            await request.response_queue.put(response)
    
    async def _handle_acquire(self, request: LockRequest) -> LockResponse:
        """Try to acquire a lock."""
        resource = request.resource
        
        # Create lock state if needed
        if resource not in self.locks:
            self.locks[resource] = LockState()
        
        lock = self.locks[resource]
        
        # Check if lock is expired
        if lock.holder and self.now >= lock.lease_expiry:
            print(f"[{self.now:.1f}] {self.name}: Lock on {resource} "
                  f"expired (was held by {lock.holder})")
            lock.holder = None
        
        # Try to acquire
        if lock.holder is None:
            lock.holder = request.client_id
            lock.token = self.next_token
            self.next_token += 1
            lock.lease_expiry = self.now + self.lease_duration
            
            print(f"[{self.now:.1f}] {self.name}: Granted lock on {resource} "
                  f"to {request.client_id} (token {lock.token})")
            
            return LockResponse(True, token=lock.token)
        
        elif lock.holder == request.client_id:
            # Renew lease for current holder
            lock.lease_expiry = self.now + self.lease_duration
            print(f"[{self.now:.1f}] {self.name}: Renewed lease on {resource} "
                  f"for {request.client_id}")
            return LockResponse(True, token=lock.token)
        
        else:
            # Lock is held by someone else
            return LockResponse(False, 
                              message=f"Lock held by {lock.holder}")
    
    async def _handle_release(self, request: LockRequest) -> LockResponse:
        """Release a lock."""
        resource = request.resource
        
        if resource not in self.locks:
            return LockResponse(False, message="Lock not found")
        
        lock = self.locks[resource]
        
        if lock.holder == request.client_id:
            print(f"[{self.now:.1f}] {self.name}: Released lock on {resource} "
                  f"by {request.client_id}")
            lock.holder = None
            return LockResponse(True)
        else:
            return LockResponse(False, 
                              message=f"Lock not held by {request.client_id}")
```

## Lock Clients

Clients acquire locks, do work in critical sections, and release locks:

```python
class LockClient(Process):
    """Client that acquires locks to access resources."""
    
    def init(self, client_id: str, server: LockServer, 
             resource: str, work_duration: float):
        self.client_id = client_id
        self.server = server
        self.resource = resource
        self.work_duration = work_duration
        self.current_token: Optional[int] = None
        
    async def run(self):
        """Acquire lock, do work, release lock."""
        # Try to acquire lock
        acquired = await self.acquire_lock()
        
        if not acquired:
            print(f"[{self.now:.1f}] {self.client_id}: Failed to acquire lock")
            return
        
        # Do work with the lock held
        print(f"[{self.now:.1f}] {self.client_id}: Starting critical section "
              f"(token {self.current_token})")
        await self.timeout(self.work_duration)
        print(f"[{self.now:.1f}] {self.client_id}: Finished critical section")
        
        # Release lock
        await self.release_lock()
    
    async def acquire_lock(self) -> bool:
        """Request lock from server."""
        response_queue = Queue(self._env)
        request = LockRequest(
            client_id=self.client_id,
            resource=self.resource,
            operation="acquire",
            response_queue=response_queue
        )
        
        await self.server.request_queue.put(request)
        response = await response_queue.get()
        
        if response.success:
            self.current_token = response.token
            return True
        return False
    
    async def release_lock(self):
        """Release lock back to server."""
        response_queue = Queue(self._env)
        request = LockRequest(
            client_id=self.client_id,
            resource=self.resource,
            operation="release",
            response_queue=response_queue
        )
        
        await self.server.request_queue.put(request)
        await response_queue.get()
        self.current_token = None
```

Let's run a simple simulation where multiple clients compete for the same lock:

```python
def run_basic_simulation():
    """Simulate multiple clients competing for a lock."""
    env = Environment()
    
    # Create lock server
    server = LockServer(env, "Server1", lease_duration=5.0)
    
    # Create clients that want the same resource
    client1 = LockClient(env, "Client1", server, "database", work_duration=3.0)
    client2 = LockClient(env, "Client2", server, "database", work_duration=2.0)
    client3 = LockClient(env, "Client3", server, "database", work_duration=4.0)
    
    env.run(until=20)


if __name__ == "__main__":
    run_basic_simulation()
```

When you run this, you'll see clients taking turns acquiring the lock.
The mutual exclusion property is preserved—only one client holds the lock at a time.

## Handling Failures with Lease Expiration

What happens if a client crashes while holding a lock?
Without lease expiration, the lock would be stuck forever.
Let's create a client that fails:

```python
class FailingClient(LockClient):
    """Client that crashes while holding a lock."""
    
    def init(self, client_id: str, server: LockServer, 
             resource: str, work_duration: float, fail_after: float):
        super().init(client_id, server, resource, work_duration)
        self.fail_after = fail_after
        
    async def run(self):
        """Acquire lock, work, then crash."""
        acquired = await self.acquire_lock()
        
        if not acquired:
            return
        
        print(f"[{self.now:.1f}] {self.client_id}: Starting work")
        
        # Simulate crash after some time
        await self.timeout(self.fail_after)
        print(f"[{self.now:.1f}] {self.client_id}: CRASHED!")
        # Client stops here without releasing the lock
```

Now let's see what happens:

```python
def run_failure_simulation():
    """Demonstrate lease expiration after client failure."""
    env = Environment()
    
    server = LockServer(env, "Server1", lease_duration=3.0)
    
    # Client that will crash
    failing = FailingClient(env, "FailClient", server, "database", 
                           work_duration=10.0, fail_after=1.0)
    
    # Client that waits and then tries to acquire
    client2 = LockClient(env, "Client2", server, "database", work_duration=2.0)
    
    # Start client2 after a delay
    LockClient(env, "Client2", server, "database", work_duration=2.0, initial_delay=5.0)

    env.run(until=15)
```

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

```python
class ProtectedResource:
    """A resource that validates fencing tokens."""
    
    def __init__(self, env: Environment, name: str):
        self.env = env
        self.name = name
        self.highest_token_seen = 0
        self.current_accessor: Optional[str] = None
        
    async def access(self, client_id: str, token: int, duration: float):
        """Access the resource with a fencing token."""
        if token <= self.highest_token_seen:
            print(f"[{self.env.now:.1f}] FENCING: {self.name} rejected "
                  f"{client_id} (stale token {token}, seen {self.highest_token_seen})")
            return False
        
        self.highest_token_seen = token
        self.current_accessor = client_id
        
        print(f"[{self.env.now:.1f}] {self.name}: {client_id} accessing "
              f"(token {token})")
        
        await self.env.timeout(duration)
        
        print(f"[{self.env.now:.1f}] {self.name}: {client_id} finished")
        self.current_accessor = None
        return True
```

Now let's create a client that uses fencing tokens:

```python
class FencedClient(Process):
    """Client that uses fencing tokens when accessing resources."""
    
    def init(self, client_id: str, server: LockServer, 
             resource_name: str, protected_resource: ProtectedResource,
             work_duration: float, pause_duration: float = 0):
        self.client_id = client_id
        self.server = server
        self.resource_name = resource_name
        self.protected_resource = protected_resource
        self.work_duration = work_duration
        self.pause_duration = pause_duration
        self.current_token: Optional[int] = None
        
    async def run(self):
        """Acquire lock and access resource with token."""
        # Acquire lock
        acquired = await self.acquire_lock()
        if not acquired:
            return
        
        # Simulate pause (GC, network delay, etc.)
        if self.pause_duration > 0:
            print(f"[{self.now:.1f}] {self.client_id}: Pausing for "
                  f"{self.pause_duration}s")
            await self.timeout(self.pause_duration)
            print(f"[{self.now:.1f}] {self.client_id}: Resuming")
        
        # Try to access resource with our token
        success = await self.protected_resource.access(
            self.client_id, self.current_token, self.work_duration
        )
        
        if success:
            await self.release_lock()
    
    async def acquire_lock(self) -> bool:
        """Acquire lock from server."""
        response_queue = Queue(self._env)
        request = LockRequest(
            client_id=self.client_id,
            resource=self.resource_name,
            operation="acquire",
            response_queue=response_queue
        )
        
        await self.server.request_queue.put(request)
        response = await response_queue.get()
        
        if response.success:
            self.current_token = response.token
            print(f"[{self.now:.1f}] {self.client_id}: Acquired lock "
                  f"(token {self.current_token})")
            return True
        return False
    
    async def release_lock(self):
        """Release lock."""
        response_queue = Queue(self._env)
        request = LockRequest(
            client_id=self.client_id,
            resource=self.resource_name,
            operation="release",
            response_queue=response_queue
        )
        
        await self.server.request_queue.put(request)
        await response_queue.get()
```

Now we can demonstrate split-brain prevention:

```python
def run_fencing_simulation():
    """Demonstrate fencing tokens preventing split-brain."""
    env = Environment()
    
    server = LockServer(env, "Server1", lease_duration=3.0)
    resource = ProtectedResource(env, "Database")
    
    # Client that will pause long enough for lease to expire
    client1 = FencedClient(env, "Client1", server, "db_lock", resource,
                          work_duration=2.0, pause_duration=5.0)
    
    # Client that acquires lock after client1's lease expires
    FencedClient(env, "Client2", server, "db_lock", resource,
                 work_duration=2.0, pause_duration=0, initial_delay=4.0)
    
    env.run(until=15)
```

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

Here's a simplified version with replicated lock servers:

```python
class ReplicatedLockManager:
    """Manages multiple lock servers with majority voting."""
    
    def __init__(self, env: Environment, num_servers: int = 3,
                 lease_duration: float = 5.0):
        self.env = env
        self.servers = []
        
        for i in range(num_servers):
            server = LockServer(env, f"Server{i+1}", lease_duration)
            self.servers.append(server)
        
        self.majority = (num_servers // 2) + 1
    
    async def acquire_lock(self, client_id: str, resource: str) -> Optional[int]:
        """Try to acquire lock from majority of servers."""
        responses = []
        response_queues = []
        
        # Send request to all servers
        for server in self.servers:
            response_queue = Queue(self.env)
            response_queues.append(response_queue)
            
            request = LockRequest(
                client_id=client_id,
                resource=resource,
                operation="acquire",
                response_queue=response_queue
            )
            await server.request_queue.put(request)
        
        # Collect responses
        for queue in response_queues:
            response = await queue.get()
            responses.append(response)
        
        # Check if we got majority approval
        successful = [r for r in responses if r.success]
        
        if len(successful) >= self.majority:
            # Use the highest token from successful responses
            token = max(r.token for r in successful)
            print(f"[{self.env.now:.1f}] Lock acquired by {client_id} "
                  f"({len(successful)}/{len(self.servers)} servers, token {token})")
            return token
        else:
            print(f"[{self.env.now:.1f}] Lock acquisition failed for {client_id} "
                  f"({len(successful)}/{len(self.servers)} servers)")
            return None
    
    async def release_lock(self, client_id: str, resource: str):
        """Release lock from all servers."""
        for server in self.servers:
            response_queue = Queue(self.env)
            request = LockRequest(
                client_id=client_id,
                resource=resource,
                operation="release",
                response_queue=response_queue
            )
            await server.request_queue.put(request)
            await response_queue.get()
```

A client using the replicated manager:

```python
class ReplicatedLockClient(Process):
    """Client using replicated lock manager."""
    
    def init(self, client_id: str, manager: ReplicatedLockManager,
             resource: str, work_duration: float):
        self.client_id = client_id
        self.manager = manager
        self.resource = resource
        self.work_duration = work_duration
        
    async def run(self):
        """Acquire lock from majority, do work, release."""
        token = await self.manager.acquire_lock(self.client_id, self.resource)
        
        if token is None:
            return
        
        print(f"[{self.now:.1f}] {self.client_id}: Working with lock")
        await self.timeout(self.work_duration)
        print(f"[{self.now:.1f}] {self.client_id}: Work complete")
        
        await self.manager.release_lock(self.client_id, self.resource)


def run_replicated_simulation():
    """Demonstrate replicated lock manager."""
    env = Environment()
    
    # Create manager with 3 servers
    manager = ReplicatedLockManager(env, num_servers=3, lease_duration=5.0)
    
    # Create competing clients
    client1 = ReplicatedLockClient(env, "Client1", manager, "resource", 3.0)
    
    ReplicatedLockClient(env, "Client2", manager, "resource", 2.0, initial_delay=2.0)
    
    env.run(until=15)
```

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