# Glossary

## A

<span id="ap-system">AP system</span>
:   A distributed system that prioritizes availability and partition tolerance
    according to the CAP theorem,
    remaining operational during network partitions
    but potentially returning stale or inconsistent data.

<span id="associativity">associativity</span>
:   The property of an operation where grouping does not affect the result,
    i.e., (a op b) op c = a op (b op c).
    Required for operations to be safely split across workers and recombined.

<span id="async-context-vars">async context variables</span>
:   Variables that store context information tied to the current asynchronous execution context
    rather than to a specific thread,
    allowing data such as trace IDs to flow automatically through async call chains.

<span id="at-least-once">at-least-once delivery</span>
:   Message delivery guarantee ensuring every message is delivered one or more times.
    Requires acknowledgments and message redelivery on failure but may result in duplicates.

<span id="at-most-once">at-most-once delivery</span>
:   Message delivery guarantee ensuring messages are delivered zero or one time,
    never duplicated but possibly lost.
    This is simple to implement but provides the weakest guarantee.

## B

<span id="backoff-multiplier">backoff multiplier</span>
:   The factor by which the wait time is multiplied after each failed retry attempt.
    A multiplier of 2 produces exponential backoff, doubling the delay with each retry.

<span id="backpressure">backpressure</span>
:   Mechanism to prevent overwhelming a system
    by signaling upstream components to slow down
    when downstream components cannot keep up.

<span id="buffer">buffer</span>
:   A temporary storage area that holds data while it is being transferred
    between components that operate at different speeds or rates.

## C

<span id="cache-miss">cache miss</span>
:   A failure to find requested data in a cache,
    requiring the more expensive operation of fetching it from the original source.

<span id="causal-consistency">causal consistency</span>
:   A consistency model where operations that are causally related
    are seen by all nodes in the same order,
    while unrelated operations may be observed in different orders on different nodes.

<span id="commutativity">commutativity</span>
:   The property of an operation where the order of operands does not affect the result,
    i.e., a op b = b op a.
    Together with associativity, it allows operations to be applied in any order and combined safely.

<span id="compensation">compensation</span>
:   A corrective action taken to undo the effects of a previously completed step in a saga
    when a later step fails,
    restoring the system to a consistent state without requiring distributed transactions.

<span id="concurrency">concurrency</span>
:   The execution of multiple tasks that overlap in time,
    which may or may not run simultaneously on different processors.
    Concurrency is concerned with managing multiple tasks,
    while parallelism is concerned with executing them at the same instant.

<span id="crdt">conflict-free replicated data type</span> (CRDT)
:   A data structure designed for distributed systems
    that can be replicated across nodes and merged automatically without coordination,
    guaranteeing that all replicas converge to the same state.

<span id="consumer-group">consumer group/span>
:   A set of message queue subscribers that share the workload.
    Messages are distributed among group members rather than duplicated to each.

<span id="contention">contention</span>
:   Competition between concurrent processes for access to a shared resource
    such as a lock, memory location, or I/O device,
    which can become a performance bottleneck.

<span id="context-propagation">context propagation</span>
:   Passing trace IDs, span IDs, and other metadata between services
    so that operations can be correlated in distributed tracing.

<span id="cp-system">CP system</span>
:   A distributed system that prioritizes consistency and partition tolerance
    according to the CAP theorem,
    refusing to serve requests rather than returning potentially inconsistent data
    during network partitions.

<span id="critical-section">critical section</span>
:   A portion of code that accesses a shared resource and must not be executed
    by more than one process or thread at a time,
    requiring mutual exclusion to prevent data corruption.

<span id="csrf">cross-site request forgery</span> (CSRF)
:   An attack where a malicious site tricks a user's browser into sending an authenticated request
    to another site without the user's knowledge,
    exploiting the browser's automatic inclusion of session cookies.

## D

<span id="dataclass">dataclass</span>
:   A Python class whose primary purpose is to hold data,
    created using the `@dataclass` decorator
    which automatically generates common methods such as `__init__`, `__repr__`, and `__eq__`.

<span id="decorator">decorator</span>
:   A function that wraps another function or class
    to modify or extend its behavior without changing its source code.

<span id="decoupling">decoupling</span>
:   The design principle of reducing dependencies between components
    so that changes in one component do not require changes in others,
    enabling independent development, testing, and scaling.

<span id="delta">delta</span>
:   A record of the difference or change between two states,
    used in delta-based CRDTs to transmit only recent changes
    rather than the full state.

<span id="deque">double-ended queue</span> (deque)
:   A data structure that supports efficient insertion and removal of elements at both ends,
    combining the properties of a stack and a queue.

<span id="divide-and-conquer">divide and conquer</span>
:   An algorithm design strategy that breaks a problem into smaller subproblems,
    solves each independently, and combines the results.
    MapReduce applies this pattern to distributed data processing.

<span id="dns">Domain Name System</span> (DNS)
:   A hierarchical, distributed database that translates human-readable domain names
    such as "www.example.com" into IP addresses.
    DNS is a critical internet infrastructure component
    that enables service mobility and scales by distributing authority across millions of servers.

<span id="dnssec">DNSSEC</span>
:   DNS Security Extensions, a suite of protocols that add cryptographic signatures to DNS records,
    allowing resolvers to verify that responses are authentic and have not been tampered with,
    thereby preventing spoofing and cache poisoning attacks.

## E

<span id="eventual-consistency">eventual consistency</span>
:   A consistency model where replicas may temporarily disagree
    but are guaranteed to converge to the same state
    if no new updates are made for a sufficient period.

<span id="exactly-once">exactly-once delivery</span>
:   Message delivery guarantee ensuring each message is processed exactly once.
    This is difficult to achieve in practice.

<span id="exponential-backoff">exponential backoff</span>
:   A retry strategy where the wait time between attempts increases exponentially after each failure,
    reducing load on an overloaded system and preventing retry storms.

## F

<span id="fan-out">fan-out</span>
:   Pattern where one message or request triggers multiple downstream operations,
    such as publishing to multiple subscribers or calling multiple services in parallel.

<span id="fault-tolerance">fault tolerance</span>
:   The ability of a system to continue operating correctly
    in the presence of failures of some of its components.

<span id="fencing-token">fencing token</span>
:   A monotonically increasing number issued with each lock grant
    that a protected resource uses to reject requests from stale lock holders,
    preventing split-brain data corruption.

<span id="future">future</span>
:   An object representing the result of an asynchronous computation that may not have completed yet.
    The result can be retrieved once the computation finishes,
    allowing the caller to do other work in the meantime.

## G

<span id="granularity">granularity</span>
:   The size of the units into which work is divided.
    Fine-grained tasks are small and numerous while coarse-grained tasks are large and few.
    The right granularity balances the benefits of parallelism against the overhead of coordination.

<span id="grow-only-counter">grow-only counter</span>
:   A CRDT that supports only increment operations,
    with each node tracking its own count
    and the total computed as the sum across all nodes.

## H

<span id="happens-before">happens-before relation</span>
:   A partial ordering of events in a distributed system
    where event A happens-before event B if A could have causally influenced B.
    Used to reason about consistency and the ordering of concurrent operations.

<span id="hash-code">hash code</span>
:   A fixed-size integer derived from data by a hash function,
    used to quickly locate data in hash tables.
    Good hash functions distribute values uniformly and minimize collisions.

<span id="http-header">HTTP header</span>
:   A key-value pair sent at the start of an HTTP request or response
    that provides metadata such as content type, authentication tokens, or caching directives.

<span id="http-status-code">HTTP status code</span>
:   A three-digit number in an HTTP response indicating the result of the request.
    Codes in the 200s indicate success, 400s indicate client errors,
    and 500s indicate server errors.

## I

<span id="idempotence">idempotence</span>
:   Describing an operation that produces the same result whether applied once or multiple times.
    Idempotent operations are safe to retry in at-least-once delivery systems.

## J

<span id="json">JSON</span>
:   JavaScript Object Notation, a lightweight text-based format for representing structured data
    as key-value pairs, arrays, and nested objects.
    Widely used for data exchange between web services.

## K

## L

<span id="lww-register">last-write-wins register</span>
:   A CRDT that resolves concurrent writes by keeping the value with the highest timestamp,
    discarding earlier writes.
    Simple to implement but may silently lose updates.

<span id="lease">lease</span>
:   A time-limited grant of a resource or lock that expires automatically
    if not renewed by the holder,
    allowing the system to recover from client failures without manual intervention.

<span id="lease-based-lock">lease-based lock</span>
:   A distributed lock that is held for a limited duration and must be periodically renewed,
    so that the lock is automatically released if the holder crashes or becomes unreachable.

<span id="linearizability">linearizability</span>
:   A strong consistency model where every operation appears to take effect instantaneously
    at some point between its start and completion,
    making the system behave as if there were a single copy of the data.

<span id="livelock">livelock</span>
:   A situation where two or more processes continually change state in response to each other
    without making progress,
    similar to deadlock but with processes that are not blocked, only unproductive.

<span id="load-balancing">load balancing</span>
:   The distribution of incoming requests or work across multiple servers or workers
    to prevent any single component from becoming a bottleneck
    and to make efficient use of available resources.

<span id="logical-clock">logical clock</span>
:   A mechanism for ordering events in a distributed system without using physical time,
    such as a Lamport clock or vector clock,
    by assigning monotonically increasing counters to events.

## M

<span id="message-broker">message broker</span>
:   A middleware component that receives messages from producers, stores them,
    and routes them to consumers.
    It decouples senders from receivers and may provide durability, ordering, and filtering.

<span id="microservice">microservice</span>
:   An architectural style where an application is built as a collection of small,
    independently deployable services,
    each responsible for a specific business capability and communicating over a network.

<span id="mutex">mutex</span>
:   A synchronization primitive that grants exclusive access to a shared resource,
    allowing only one thread or process to hold it at a time
    and blocking others until it is released.

<span id="mutual-exclusion">mutual exclusion</span>
:   The guarantee that only one process or thread accesses a shared resource at any given time,
    preventing race conditions and data corruption in concurrent systems.

## N

<span id="negative-cache">negative cache</span>
:   A cache that stores records indicating that a lookup returned no result,
    such as a non-existent domain name,
    so that repeated queries for the same missing resource are answered locally
    rather than forwarded to authoritative servers.

<span id="negative-feedback-loop">negative feedback loop</span>
:   A control mechanism where a system's output feeds back to reduce its input,
    stabilizing the system around a target state.
    Backpressure in distributed systems is an example of this pattern.

<span id="network-partition">network partition</span>
:   A failure that splits a distributed system into two or more groups of nodes
    that cannot communicate with each other,
    forcing a choice between consistency and availability according to the CAP theorem.

## O

<span id="oauth-scope">OAuth scope</span>
:   A string that specifies the permissions an application is requesting from a user,
    limiting what the application can do with the access token it receives.

<span id="oauth-token">OAuth token</span>
:   A credential issued by an authorization server that grants an application
    limited access to a user's resources on another service
    without exposing the user's password.

<span id="op-based-crdt">operation-based CRDT</span>
:   A CRDT that replicates by broadcasting individual operations to all replicas.
    Requires operations to be commutative so they can be applied in any order.

## P

<span id="partial-order">partial order</span>
:   A relation that is reflexive, antisymmetric, and transitive,
    but where not all pairs of elements are necessarily comparable.
    The happens-before relation is a partial order on events in a distributed system.

<span id="partition-tolerance">partition tolerance</span>
:   The ability of a distributed system to continue operating correctly
    even when network partitions prevent some nodes from communicating with others.

<span id="pn-counter">positive-negative counter</span>
:   A CRDT counter that supports both increment and decrement operations
    by maintaining one grow-only counter for increments and another for decrements,
    with the value being their difference.

<span id="priority-queue">priority queue</span>
:   A data structure where each element has an associated priority
    and elements are removed in priority order rather than insertion order.

<span id="publish-subscribe">publish-subscribe</span>
:   Messaging pattern where publishers send messages to topics
    and subscribers receive all messages from topics they're interested in.
    This pattern decouples senders from receivers.

## Q

## R

<span id="recursive-resolver">recursive resolver</span>
:   A DNS server that accepts queries from clients and resolves them on the client's behalf
    by walking the DNS hierarchy from root servers down to authoritative name servers,
    caching responses to answer future queries more quickly.

<span id="root-server">root server</span>
:   One of the thirteen logical DNS servers at the top of the DNS hierarchy
    that know the authoritative name servers for each top-level domain.
    In practice, root servers are implemented as many physical servers
    distributed worldwide using anycast addressing.

<span id="root-span">root span</span>
:   The first span in a trace, representing the top-level operation that initiated the request
    and serving as the root of the trace's span tree.

<span id="round-robin-polling">round-robin polling</span>
:   A scheduling strategy that cycles through a list of items in fixed rotation,
    giving each one a turn in order to distribute work or checks evenly.

## S

<span id="saga">saga</span>
:   A apttern in which a multi-step transaction is implemented as a sequence of local transactions,
    each with a compensating action to undo its effects if the overall transaction fails.

<span id="sampling">sampling</span>
:   Recording only a fraction of traces in distributed tracing
    to reduce overhead and storage requirements.

<span id="schema">schema</span>
:   A formal description of the structure and types of data,
    used to validate that data conforms to an expected format.
    Common in databases and data interchange formats such as JSON and Avro.

<span id="semaphore">semaphore</span>
:   A synchronization primitive that controls access to a shared resource
    by maintaining a counter representing the number of available permits,
    allowing up to that many concurrent accessors.

<span id="sequential-consistency">sequential consistency</span>
:   A consistency model where all operations appear to execute in some total order
    that is consistent with the order seen by each individual process.

<span id="single-sign-on">single sign-on</span>
:   An authentication scheme that allows a user to log in once
    and gain access to multiple applications or services
    without re-entering credentials for each one.

<span id="singleton">singleton</span>
:   A design pattern that restricts a class to a single instance
    and provides a global access point to it.

<span id="span">span</span>
:   A named, timed operation representing a single unit of work within a distributed trace.
    Spans can be nested to form a tree that represents the full execution of a request.

<span id="speculative-execution">speculative execution</span>
:   Running multiple instances of a task in parallel and using the result of whichever completes first,
    discarding the others,
    to reduce the impact of slow or failed workers.

<span id="split-brain">split-brain scenario</span>
:   A situation where two or more nodes in a distributed system each believe they hold exclusive control
    over a resource, typically caused by a network partition,
    leading to conflicting writes and data inconsistency.

<span id="state-based-crdt">state-based CRDT</span>
:   A CRDT that replicates by periodically sending the full state to other replicas,
    which merge it using a commutative, associative, and idempotent merge function.

<span id="strong-consistency">strong consistency</span>
:   A consistency model where all reads return the most recently written value,
    as if the system had a single authoritative copy of the data.

<span id="strong-eventual-consistency">strong eventual consistency</span>
:   A consistency model guaranteeing that any two replicas
    that have received the same set of updates will have identical states,
    regardless of the order in which those updates arrived.

## T

<span id="thread-local-storage">thread-local storage</span>
:   A mechanism that provides each thread with its own private copy of a variable,
    preventing interference between threads without requiring synchronization.

<span id="ttl">time to live</span> (TTL)
:   A value attached to a DNS record or cached entry that specifies
    how long it may be stored before it must be discarded and re-fetched.
    Low TTLs allow changes to propagate quickly but increase query load;
    high TTLs reduce load but slow propagation of updates.

<span id="tld">top-level domain</span>
:   The rightmost label in a domain name, such as `.com`, `.org`, or `.net`,
    managed by a dedicated set of DNS servers that know the authoritative name servers
    for every domain registered under that suffix.

<span id="total-order">total order</span>
:   A relation that is reflexive, antisymmetric, and transitive,
    and where every pair of elements is comparable.
    Unlike a partial order, every two elements can be ordered relative to each other.

<span id="trace">trace</span>
:   The complete journey of a request through a distributed system,
    identified by a unique trace ID and composed of multiple spans forming a tree.

<span id="trace-collector">trace collector</span>
:   A service that receives spans from instrumented applications,
    assembles them into complete traces,
    and stores or forwards them to a backend for analysis and visualization.

<span id="tcp">Transmission Control Protocol</span> (TCP)
:   A network protocol that provides reliable, ordered delivery of data over the internet,
    built on top of the unreliable UDP protocol.
    TCP uses sequence numbers, acknowledgments, retransmission, and sliding windows
    to handle packet loss, reordering, and congestion automatically.

<span id="trust-anchor">trust anchor</span>
:   A certificate or public key that is trusted unconditionally
    and serves as the root from which the validity of other certificates in a chain is established.

## U

## V

<span id="vector-clock">vector clock</span>
:   A data structure used to capture causality in distributed systems,
    consisting of one counter per process.
    Comparing two vector clocks determines whether events are causally related
    or concurrent.

## W

<span id="work-stealing">work stealing</a>
:   A scheduling strategy where each worker maintains a local task queue
    and idle workers take tasks from others' queues
    in order to minimize contention while balancing load.

## X

## Y

## Z
