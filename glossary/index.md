# Glossary


## A

<span id="associativity">associativity</span>
:   FIXME

<span id="async-context-vars">async context variables</span>
:   FIXME

<span id="at-least-once">at-least-once delivery</span>
:   Message delivery guarantee ensuring every message is delivered one or more times.
    Requires acknowledgments and message redelivery on failure but may result in duplicates.

<span id="at-most-once">at-most-once delivery</span>
:   Message delivery guarantee ensuring messages are delivered zero or one time,
    never duplicated but possibly lost.
    This is simple to implement but provides the weakest guarantee.

## B

<span id="backoff-multiplier">backoff multiplier</span>
:   FIXME

<span id="backpressure">backpressure</span>
:   Mechanism to prevent overwhelming a system
    by signaling upstream components to slow down
    when downstream components cannot keep up.

<span id="buffer">buffer</span>
:   FIXME

## C

<span id="cache-miss">cache miss</span>
:   FIXME

<span id="commutativity">commutativity</span>
:   FIXME

<span id="crdt">conflict-free replicated data type</span> (CRDT)
:   FIXME

<span id="consumer-group">consumer group/span>
:   A set of message queue subscribers that share the workload.
    Messages are distributed among group members rather than duplicated to each.

<span id="contention">contention/span>
:   FIXME

<span id="context-propagation">context propagation</span>
:   Passing trace IDs, span IDs, and other metadata between services
    so that operations can be correlated in distributed tracing.

## D

<span id="dataclass">dataclass</span>
:   FIXME

<span id="decorator">decorator</span>
:   FIXME

<span id="decoupling">decoupling</span>
:   FIXME

<span id="delta">delta</span>
:   FIXME

<span id="deque">double-ended queue</span> (deque)
:   FIXME

<span id="divide-and-conquer">divide and conquer</span>
:   FIXME

## E

<span id="exactly-once">exactly-once delivery</span>
:   Message delivery guarantee ensuring each message is processed exactly once.
    This is difficult to achieve in practice.

<span id="exponential-backoff">exponential backoff</span>
:   FIXME

## F

<span id="fan-out">fan-out</span>
:   Pattern where one message or request triggers multiple downstream operations,
    such as publishing to multiple subscribers or calling multiple services in parallel.

<span id="future">future</span>
:   FIXME

## G

<span id="granularity">granulaty</span>
:   FIXME

<span id="grow-only-counter">grow-only counter</span>
:   FIXME

## H

<span id="hash-code">hash code</span>
:   FIXME

<span id="http-header">HTTP header</span>
:   FIXME

<span id="http-status-code">HTTP status code</span>
:   FIXME

## I

<span id="idempotent">idempotent</span>
:   FIXME

## J

<span id="json">JSON</span>
:   FIXME

## L

<span id="lww-register">last-write-wins register</span>
:   FIXME

<span id="livelock">livelock</span>
:   FIXME

<span id="load-balancing">load balancing</span>
:   FIXME

## M

<span id="message-broker">message broker</span>
:   FIXME

<span id="microservice">microservice</span>
:   FIXME

## N

<span id="negative-feedback-loop">negative feedback loop</span>
:   FIXME

<span id="network-partition">network partition</span>
:   FIXME

## O

<span id="op-based-crdt">operation-based CRDT</span>
:   FIXME

## P

<span id="partition-tolerance">partition tolerance</span>
:   FIXME

<span id="pn-counter">positive-negative counter</span>
:   FIXME

<span id="priority-queue">priority queue</span>
:   FIXME

<span id="publish-subscribe">publish-subscribe</span>
:   Messaging pattern where publishers send messages to topics
    and subscribers receive all messages from topics they're interested in.
    This pattern decouples senders from receivers.

## R

<span id="root-span">root span</span>
:   FIXME

<span id="round-robin-polling">round-robin polling</span>
:   FIXME

## S

<span id="sampling">sampling</span>
:   Recording only a fraction of traces in distributed tracing
    to reduce overhead and storage requirements.

<span id="schema">schema</span>
:   FIXME

<span id="singleton">singleton</span>
:   FIXME

<span id="span">span</span>
:   FIXME

<span id="state-based-crdt">state-based CRDT</span>
:   FIXME

<span id="strong-eventual-consistency">strong eventual consistency</span>
:   FIXME

## T

<span id="thread-local-storage">thread-local storage</span>
:   FIXME

<span id="trace">trace</span>
:   The complete journey of a request through a distributed system,
    identified by a unique trace ID and composed of multiple spans forming a tree.

<span id="trace-collector">trace collector</span>
:   FIXME

## W

<span id="work-stealing">work stealing</a>
:   A scheduling strategy where each worker maintains a local task queue
    and idle workers take tasks from others' queues
    in order to minimize contention while balancing load.
