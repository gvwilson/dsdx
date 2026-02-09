# Glossary

<span id="at-least-once">at-least-once delivery</span>
:   Message delivery guarantee ensuring every message is delivered one or more times.
    Requires acknowledgments and message redelivery on failure but may result in duplicates.

<span id="at-most-once">at-most-once delivery</span>
:   Message delivery guarantee ensuring messages are delivered zero or one time,
    never duplicated but possibly lost.
    This is simple to implement but provides the weakest guarantee.

<span id="backoff-multiplier">backoff multiplier</span>
:   FIXME

<span id="backpressure">backpressure</span>
:   Mechanism to prevent overwhelming a system
    by signaling upstream components to slow down
    when downstream components cannot keep up.

<span id="buffer">buffer</span>
:   FIXME

<span id="consumer-group">consumer group/span>
:   A set of message queue subscribers that share the workload.
    Messages are distributed among group members rather than duplicated to each.

<span id="dataclass">dataclass</span>
:   FIXME

<span id="decoupling">decoupling</span>
:   FIXME

<span id="exactly-once">exactly-once delivery</span>
:   Message delivery guarantee ensuring each message is processed exactly once.
    This is difficult to achieve in practice.

<span id="exponential-backoff">exponential backoff</span>
:   FIXME

<span id="fan-out">fan-out</span>
:   Pattern where one message or request triggers multiple downstream operations, such as publishing to multiple subscribers or calling multiple services in parallel.

<span id="json">JSON</span>
:   FIXME

<span id="message-broker">message broker</span>
:   FIXME

<span id="negative-feedback-loop">negative feedback loop</span>
:   FIXME

<span id="priority-queue">priority queue</span>
:   FIXME

<span id="publish-subscribe">publish-subscribe</span>
:   Messaging pattern where publishers send messages to topics and subscribers receive all messages from topics they're interested in. Decouples senders from receivers.

<span id="round-robin-polling">round-robin polling</span>
:   FIXME

<span id="work-stealing">work stealing</a>
:   A scheduling strategy where each worker maintains a local task queue
    and idle workers take tasks from others' queues
    in order to minimize contention while balancing load.
