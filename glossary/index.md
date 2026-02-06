# Glossary

ACID
:   Properties of traditional database transactions: Atomicity (all-or-nothing), Consistency (valid state transitions), Isolation (concurrent transactions don't interfere), and Durability (committed changes persist).

anti-entropy
:   Background process in distributed systems that compares replicas and repairs inconsistencies to ensure eventual convergence, often using techniques like Merkle trees.

associativity
:   Mathematical property where grouping doesn't affect the result: (A + B) + C = A + (B + C). Required for CRDT merge operations and MapReduce reduce functions.

at-least-once delivery
:   Message delivery guarantee ensuring every message is delivered one or more times. Requires acknowledgments and message redelivery on failure but may result in duplicates.

at-most-once delivery
:   Message delivery guarantee ensuring messages are delivered zero or one time, never duplicated but possibly lost. Simplest to implement but provides the weakest guarantee.

authorization code
:   In OAuth 2.0, a short-lived token issued to the client after user authentication and consent, which the client exchanges for an access token.

backpressure
:   Mechanism to prevent overwhelming a system by signaling upstream components to slow down when downstream components cannot keep up with the rate of messages or requests.

bitfield
:   Compact data structure using individual bits to represent boolean states. In BitTorrent, indicates which pieces a peer possesses.

CAP theorem
:   States that a distributed system can provide at most two of three guarantees: Consistency (all nodes see same data), Availability (system responds to requests), and Partition tolerance (works despite network failures).

causal delivery
:   Message delivery order where if operation A happened-before operation B, then A is delivered before B. Required for operation-based CRDTs.

choreography
:   Saga implementation pattern where services communicate through events and each service decides its next action independently, without a central coordinator. Decentralized but harder to monitor.

choking algorithm
:   In BitTorrent, strategy where peers limit concurrent uploads to their best uploaders (typically 4-5) to maximize bandwidth efficiency by focusing on productive connections.

combiner function
:   In MapReduce, an optional local reduce operation that runs on mapper output before shuffling, reducing network traffic by pre-aggregating data.

commutativity
:   Mathematical property where order doesn't affect the result: A + B = B + A. Essential for CRDTs and enables operations to be applied in any order while achieving the same final state.

compensating transaction
:   Forward operation in a Saga that semantically undoes the effects of a previously completed transaction (e.g., refund payment, cancel reservation). Must be idempotent and retryable.

conflict-free replicated data type (CRDT)
:   Data structure designed so concurrent updates on different replicas can always be merged automatically without conflicts, guaranteeing eventual convergence.

consensus
:   Process by which distributed nodes agree on a single value or decision despite failures. Algorithms like Paxos and Raft provide consensus guarantees.

consistent hashing
:   Technique for distributing data across nodes where adding or removing nodes causes minimal data movement. Used in distributed hash tables and key-value stores.

consumer group
:   Set of message queue subscribers that share the workload, with messages distributed among group members rather than duplicated to each. Enables parallel processing.

context propagation
:   Passing trace IDs, span IDs, and other metadata between services so operations can be correlated across service boundaries in distributed tracing.

CvRDT (state-based CRDT)
:   CRDT variant where replicas send their entire state and merge states using operations that are commutative, associative, and idempotent.

CmRDT (operation-based CRDT)
:   CRDT variant where replicas send operations (deltas) that must commute. Requires reliable delivery but has lower network overhead than state-based CRDTs.

dead letter queue
:   Queue for messages that cannot be processed successfully after multiple retry attempts, enabling later analysis and manual intervention.

dirty read
:   Reading data that has been modified but not yet committed by another transaction. In eventually consistent systems, transactions may see intermediate states from in-progress Sagas.

distributed hash table (DHT)
:   Decentralized system for storing key-value pairs across multiple nodes. In BitTorrent, enables peer discovery without central trackers using the Kademlia algorithm.

distributed lock
:   Mechanism ensuring only one process across multiple machines can hold a lock on a resource at any given time, coordinating access to shared resources.

distributed tracing
:   System for tracking requests as they flow through multiple services, creating a tree of spans that shows timing, dependencies, and performance bottlenecks.

end game mode
:   BitTorrent optimization where peers nearing completion aggressively request remaining pieces from multiple peers and cancel duplicates when received, preventing slow final pieces.

ephemeral node
:   ZooKeeper node that automatically deletes when the client session that created it ends, useful for implementing locks and leader election.

eventual consistency
:   Guarantee that if no new updates are made, all replicas will eventually converge to the same state. Trades immediate consistency for availability and partition tolerance.

exactly-once delivery
:   Message delivery guarantee ensuring each message is processed exactly once. Difficult to achieve; requires idempotent operations and deduplication tracking.

fan-out
:   Pattern where one message or request triggers multiple downstream operations, such as publishing to multiple subscribers or calling multiple services in parallel.

fencing token
:   Monotonically increasing number issued with each lock acquisition. Protected resources reject operations with older tokens, preventing split-brain scenarios where multiple processes believe they hold a lock.

fork/join
:   Parallel programming pattern where tasks are recursively split (forked) into subtasks and results are combined (joined). Implemented efficiently using work-stealing schedulers.

gossip protocol
:   Communication pattern where nodes periodically exchange information with random peers, spreading updates epidemically through the cluster for failure detection and membership.

grow-only counter (g-counter)
:   CRDT that can only increment. Each replica maintains a vector of counters; the value is the sum of all counters; merge takes the maximum of each entry.

happens-before
:   Partial ordering of events in a distributed system. Event A happens-before event B if A could have causally influenced B, determined using vector clocks.

hinted handoff
:   Technique where writes intended for a temporarily unavailable node are stored on another node with a "hint" and replayed when the target node recovers.

idempotence
:   Property where applying an operation multiple times has the same effect as applying it once. Essential for retry logic and exactly-once semantics in distributed systems.

inverted index
:   Data structure mapping words to documents containing them, fundamental for search engines. Can be built efficiently using MapReduce.

isolation
:   Database property ensuring concurrent transactions don't interfere with each other. Eventual consistent systems sacrifice isolation for availability.

last-write-wins (LWW)
:   Conflict resolution strategy using timestamps where the write with the highest timestamp (or deterministic tiebreaker) wins. Simple but may lose concurrent updates.

lease
:   Time-limited permission to access a resource. If the holder fails to renew before expiration, the lease is automatically released, providing fault tolerance.

leecher
:   In BitTorrent, a peer that is downloading the file and does not yet have all pieces. Distinguished from seeders who have the complete file.

Liskov Substitution Principle (LSP)
:   Design principle stating that objects of a superclass should be replaceable with objects of subclasses without breaking the application.

LWW-register
:   CRDT register using last-write-wins conflict resolution based on timestamps and replica IDs for deterministic ordering.

MapReduce
:   Programming model for processing large datasets across distributed clusters. Map phase transforms input independently; reduce phase aggregates by key after shuffling.

Merkle tree
:   Tree of cryptographic hashes where each non-leaf node is the hash of its children. Efficiently identifies differences between replicas for anti-entropy.

mutual exclusion
:   Property ensuring only one process can access a critical section or resource at a time, fundamental requirement for distributed locks.

OAuth
:   Authorization framework enabling applications to obtain limited access to user accounts without exposing passwords, using tokens with specific scopes and lifetimes.

OpenID Connect (OIDC)
:   Identity layer built on OAuth 2.0 that adds user authentication through ID tokens, enabling single sign-on while OAuth provides API authorization.

operation-based CRDT
:   See CmRDT.

optimistic locking
:   Concurrency control method assuming conflicts are rare. Transactions proceed without locks but check for conflicts before committing, retrying if conflicts detected.

optimistic unchoking
:   BitTorrent strategy where peers periodically upload to a random peer regardless of contribution, giving new peers opportunity to participate and discovering faster peers.

observed-remove set (OR-Set)
:   CRDT set where elements are tagged with unique identifiers. Add-wins semantics: concurrent add and remove results in element being present.

orchestration
:   Saga implementation pattern where a central coordinator directs each service's actions, making the workflow easier to understand and monitor but creating a coordination point.

partition
:   Network failure where nodes are divided into groups that cannot communicate. Systems must choose between consistency and availability during partitions (CAP theorem).

partition tolerance
:   System's ability to continue operating despite network partitions. One of three properties in CAP theorem.

peer-to-peer (P2P)
:   Network architecture where participants (peers) share resources directly with each other without requiring central servers. BitTorrent is a prominent example.

pivot transaction
:   Last transaction in a Saga that cannot be compensated (e.g., sending email, shipping goods). Sagas should be designed with risky operations early and irreversible operations last.

Positive-Negative Counter (PN-Counter)
:   CRDT supporting both increment and decrement using two G-Counters: one for increments, one for decrements. Value is increments minus decrements.

probabilistic sampling
:   Tracing strategy where each trace has a random probability of being recorded (e.g., 10%), reducing overhead while maintaining statistical representativeness.

publish-subscribe
:   Messaging pattern where publishers send messages to topics and subscribers receive all messages from topics they're interested in. Decouples senders from receivers.

quorum
:   Minimum number of nodes that must participate in an operation for it to succeed. Common pattern: for N replicas, read from R nodes and write to W nodes where R + W > N ensures consistency.

Raft
:   Consensus algorithm designed for understandability. Nodes elect a leader who manages a replicated log, providing strong consistency through majority agreement.

rarest first
:   BitTorrent piece selection strategy prioritizing downloading the rarest pieces in the swarm first, ensuring piece diversity and swarm health.

read repair
:   Technique where inconsistencies detected during reads are immediately repaired by updating lagging replicas with the most recent version.

reduce
:   MapReduce phase that aggregates values by key. Reduce functions must be associative and commutative to enable parallelization and fault tolerance.

refresh token
:   Long-lived OAuth token used to obtain new access tokens without user interaction when they expire, maintaining sessions without storing passwords.

replication
:   Maintaining copies of data on multiple nodes for fault tolerance and availability. Can be synchronous (waiting for acknowledgments) or asynchronous.

replication factor
:   Number of copies maintained for each piece of data. Higher replication increases availability and read throughput but requires more storage and write coordination.

resource server
:   In OAuth 2.0, the API server hosting protected resources that validates access tokens and enforces scope-based access control.

saga
:   Pattern for managing distributed transactions as a sequence of local transactions with compensating transactions for rollback, providing eventual consistency without distributed locks.

sampling
:   Recording only a fraction of traces in distributed tracing to manage overhead and storage costs while maintaining observability.

scope
:   In OAuth 2.0, specific permissions granted by an access token (e.g., "read:profile", "write:posts"), enabling fine-grained access control.

seeder
:   In BitTorrent, a peer that has downloaded the complete file and continues uploading to help others. Essential for swarm health.

semantic locking
:   Preventing dirty reads during Saga execution by marking records as "pending" so users don't see intermediate states from incomplete transactions.

shard
:   Horizontal partition of a database where each partition contains a subset of data. Enables scaling by distributing load across multiple servers.

shuffle
:   MapReduce phase between map and reduce where intermediate key-value pairs are partitioned, sorted by key, and distributed to reduce workers.

sloppy quorum
:   Variant of quorum where any N healthy nodes can accept writes rather than requiring specific replicas, improving availability during failures.

span
:   Unit of work in distributed tracing representing a single operation with timing information, tags, logs, and parent-child relationships forming a tree.

speculative execution
:   MapReduce optimization launching backup copies of slow tasks (stragglers) on other workers. First copy to complete wins; others are discarded.

split-brain
:   Failure scenario where multiple nodes believe they are the leader or hold a lock simultaneously, potentially causing data corruption. Prevented using fencing tokens.

state-based CRDT
:   See CvRDT.

strong eventual consistency
:   CRDT guarantee that replicas receiving the same updates will be in the same state, regardless of delivery order or timing.

swarm
:   In BitTorrent, all peers participating in sharing a particular file, including both seeders and leechers.

tit-for-tat
:   BitTorrent incentive mechanism where peers upload to those who upload to them, encouraging cooperation without central enforcement.

tombstone
:   Marker indicating a deleted item. Used in CRDTs and eventually consistent systems to propagate deletions without losing information about what was deleted.

torrent
:   BitTorrent metadata file describing files to download, piece hashes for verification, and tracker URLs for peer discovery.

trace
:   Complete journey of a request through a distributed system, identified by a unique trace ID and composed of multiple spans forming a tree.

tracker
:   BitTorrent server coordinating peers by maintaining lists of participants in each swarm and facilitating peer discovery.

two-phase commit (2PC)
:   A distributed transaction protocol where a coordinator asks all participants to prepare, then either commits or aborts based on unanimous agreement. Provides strong consistency but can block resources and has availability limitations.

vector clock
:   Data structure tracking causality in distributed systems. Maps each replica to a counter; used to determine if events are concurrent or causally ordered.

work-stealing
:   Scheduling strategy where each worker maintains a local task queue and idle workers "steal" tasks from others' queues, minimizing contention while balancing load.
