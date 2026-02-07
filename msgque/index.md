# A Message Queue with Publish-Subscribe

<p class="subtitle" markdown="1">loosely-coupled communication</p>

Real-world distributed systems need a way for components to communicate without being tightly coupled.
When a web server processes an order, it might need to notify the inventory system, trigger an email, update analytics, and log the transaction.
If the web server called each of these services directly, a failure in any one would block the entire operation.
This is where message queues come in.

Systems like [RabbitMQ][rabbitmq], [Apache Kafka][kafka], and [Amazon SQS][amazon-sqs]
act as intermediaries that decouple message producers from consumers.
A publisher sends messages to a named topic without knowing who (if anyone) will receive them.
Subscribers express interest in topics and receive messages asynchronously, processing them at their own pace.
This pattern is fundamental to event-driven architectures used throughout the industry—from LinkedIn's data pipeline that processes billions of events daily, to Netflix's recommendation engine that reacts to viewing patterns, to real-time analytics platforms that aggregate clickstream data.

## Understanding the Publish-Subscribe Pattern

In the publish-subscribe pattern, publishers send messages to topics (sometimes called channels or exchanges).
The message broker maintains subscriptions—mappings from topics to interested consumers.
When a message arrives, the broker delivers it to all current subscribers of that topic.
This is called fan-out: one message can reach many consumers.

The pattern provides several crucial benefits.
First, publishers and subscribers don't need to know about each other—they only share knowledge of topic names.
Second, the system can scale independently: you can add more publishers or subscribers without modifying existing code.
Third, the broker provides buffering: if consumers are slow or temporarily unavailable, messages wait in queues rather than being lost.

## Our Implementation

We'll build a message queue system using asimpy, a discrete event simulation framework based on Python's async/await syntax.
Asimpy lets us model concurrent systems using coroutines without dealing with actual threads or network connections.
This makes the code simpler and deterministic—perfect for understanding the core concepts.

Our system has three main components: publishers that send messages, a broker that routes messages to topics, and subscribers that receive and process messages.
Let's start with the message broker itself:

<div data-inc="message.py" data-filter="inc=message"></div>

The `Message` class represents data flowing through our system.
Each message has a topic (like "orders" or "user-activity"), content (the actual data), a unique ID, and a timestamp.
In a real system, messages would contain rich structured data, but strings are sufficient for our example.

<div data-inc="broker.py" data-filter="inc=broker"></div>

The broker maintains a dictionary mapping topics to lists of queues.
When a message is published, the broker looks up the topic and places the message in each subscriber's queue.
Using separate queues per subscriber ensures that a slow consumer doesn't block others—this is a key property of the pattern.

Unlike many message queue implementations that would drop messages when queues fill up, our asimpy queues grow unbounded.
In a real system, you'd want to enforce limits and implement backpressure or message dropping policies.
We'll discuss delivery semantics later.

Now let's implement publishers.
A publisher sends messages to topics at some rate:

<div data-inc="publisher.py" data-filter="inc=publisher"></div>

This publisher sends messages at regular intervals.
Real publishers would react to external events (like HTTP requests or database changes), but timed generation works well for simulation.
The `await self.timeout()` pauses this process and resumes after the specified time.

Notice that we inherit from `Process`, which is asimpy's base class for active components.
The `init()` method is called during construction to set up our state, and `run()` is the coroutine that defines the publisher's behavior.

Finally, subscribers receive and process messages:

<div data-inc="subscriber.py" data-filter="inc=subscriber"></div>

The subscriber uses asimpy's `FirstOf` to wait on multiple queues simultaneously—whichever queue has a message first will complete.
This is more elegant than round-robin polling.
Real implementations use event-driven APIs or threads, but `FirstOf` captures the same semantics: we wait for any subscribed topic to produce a message.

The key point is that processing happens asynchronously: the subscriber takes messages from its queues and processes them at its own pace, independently of the publishers and other subscribers.

## Running a Simulation

Let's create a scenario with multiple publishers and subscribers to see the system in action:

<div data-inc="ex_simple.py" data-filter="inc=simulate"></div>
<div data-inc="ex_simple.txt" data-filter="head=10 + tail=6"></div>

When we run this code, we see messages being published and consumed asynchronously.
Notice how the fast `Inventory` service keeps up with orders, while the slow `Email` service falls behind.
Messages queue up waiting for processing—this is the buffering we mentioned earlier.

The `Analytics` service receives messages from multiple topics,
demonstrating how subscribers can aggregate different event streams.
This is common in real systems: a data warehouse might subscribe to dozens of topics to build a complete picture of system activity.

## Backpressure and Flow Control

So far, our broker uses unbounded queues that grow indefinitely.
This works in simulation but fails in production:
if publishers produce faster than subscribers consume, queues will eventually exhaust memory and crash the system.
The solution is *backpressure*—a mechanism where slow consumers signal upstream components to slow down.

Backpressure is fundamental to building robust distributed systems.
Without it, a single slow consumer can cascade failures throughout the system.
Consider a real-world scenario: during a traffic spike, your web servers might generate events faster than your analytics database can process them.
Without backpressure, the message queue fills up, runs out of memory, and crashes—taking down multiple services.

There are several strategies for implementing backpressure:

1.  **Bounded queues with blocking**:
    Publishers block when queues are full, naturally slowing them down.
    This provides strong backpressure but can cause publishers to stall.

1.  **Bounded queues with dropping**:
    When queues are full, new messages are dropped.
    This keeps the system running but loses data.
    Often combined with metrics so operators know data is being lost.

1.  **Adaptive rate limiting**:
    Publishers monitor queue sizes or delivery failures and dynamically adjust their publishing rate.
    This is more complex but provides smooth behavior under load.

1.  **Priority-based dropping**:
    When backpressure occurs, drop low-priority messages first, preserving critical data.

Let's implement bounded queues with message dropping and adaptive rate limiting:

<div data-inc="backpressure_broker.py" data-filter="inc=backpressure"></div>

The key change is using `Queue(env, capacity=max_queue_size)` to create bounded queues.
When a queue is full, we drop the message for that subscriber.
The broker returns `False` to signal backpressure to the publisher.

Now we need a publisher that responds to backpressure:

<div data-inc="backpressure_publisher.py" data-filter="inc=backpressure_publisher"></div>

This publisher implements exponential backoff:
when `publish()` returns `False`, it doubles its interval between messages.
When publishing succeeds, it gradually reduces the interval back to the base rate.
This creates a negative feedback loop that stabilizes the system under load.

Let's see backpressure in action:

<div data-inc="ex_backpressure.py" data-filter="inc=backpressure_simulation"></div>
<div data-inc="ex_backpressure.txt" data-filter="head=10 + tail=7"></div>

When you run this simulation,
you'll see the publisher start fast but encounter backpressure as the slow subscriber's queue fills.
The publisher adapts by slowing down,
and the system reaches equilibrium where the publishing rate matches the consumption rate.

This is exactly what happens in production systems.
RabbitMQ supports bounded queues and will reject publishes when queues are full.
Kafka uses partition limits and producer throttling.
AWS SQS returns backpressure signals when message rates exceed limits.

## Advanced Backpressure: Priority Queues

In many real systems, not all messages have equal importance.
During backpressure, you might want to preserve high-priority messages while dropping low-priority ones.
Here's how to implement priority-based backpressure:

<div data-inc="priority_backpressure.py" data-filter="inc=priority_message"></div>

<div data-inc="priority_backpressure.py" data-filter="inc=priority_broker"></div>

This broker tracks dropped messages by priority level, letting operators see which message types are being lost.
In a full implementation, you'd maintain a priority queue that allows efficient eviction of low-priority messages.
The principle remains: when backpressure occurs, preserve what matters most.

Kafka's partition assignment and compaction features provide a form of priority-based retention.
RabbitMQ supports priority queues natively.
Custom message brokers in high-frequency trading and real-time analytics
often implement sophisticated priority schemes.

## Delivery Guarantees

Our implementation provides unbounded queuing, which means messages are never dropped (assuming infinite memory).
This is closer to "at-least-once" delivery,
though we haven't implemented acknowledgments or redelivery on failure.
Let's discuss the spectrum of delivery guarantees:

-   **At-most-once delivery** ensures that messages are delivered zero or one time—never duplicated, but possibly lost.
This is achieved by dropping messages when queues are full or when subscribers are unavailable.
It's the weakest guarantee but the simplest to implement and the fastest.

-   **At-least-once delivery** ensures every message is delivered, possibly multiple times.
This requires acknowledgments: the broker keeps messages until subscribers confirm receipt.
If a subscriber crashes before acknowledging, the broker redelivers to another subscriber or retries.
Kafka and RabbitMQ support this mode.

-   **Exactly-once delivery** is the strongest guarantee: each message is processed exactly once.
This is surprisingly difficult in distributed systems due to failures and network issues.
Kafka achieves this through idempotent producers and transactional consumers—essentially assigning each message a unique ID and having consumers track which IDs they've processed.

Here's how we could extend our broker to support at-least-once delivery with acknowledgments:

<div data-inc="ack_broker.py" data-filter="inc=ackmessage"></div>

<div data-inc="ack_broker.py" data-filter="inc=ackbroker"></div>

A subscriber using this broker would call `broker.acknowledge(message.ack_id)` after successfully processing each message.
Messages not acknowledged within the timeout would be redelivered.

## Consumer Groups and Load Balancing

In production systems, we often want multiple instances of the same subscriber type to share the workload.
This is called a consumer group: messages on a topic are distributed among group members rather than duplicated to each.
Here's a simple implementation:

<div data-inc="consumer_group.py" data-filter="inc=consumer"></div>
<div data-inc="consumer_group.py" data-filter="inc=distributor"></div>

This consumer group receives messages from the broker on a single queue, then distributes them round-robin to individual consumer queues.
Each consumer in the group processes a subset of the messages, enabling parallel processing.
Real systems use more sophisticated load balancing—weighted distribution, least-loaded routing, or partition-based assignment.

## Conclusion

The publish-subscribe pattern decouples system components, enabling independent scaling and evolution.
By routing messages through a broker, we gain buffering, fan-out, and fault tolerance.
Backpressure ensures the system remains stable under load, preventing cascading failures when consumers can't keep up with producers.

The code we've written captures the essential ideas: topics, subscriptions, asynchronous delivery, queuing, and backpressure.
We've seen how asimpy's async/await syntax makes concurrent behavior natural to express, how bounded queues create backpressure, and how publishers can adapt to flow control signals.

Real systems add persistence (writing messages to disk), replication (for fault tolerance), partitioning (for parallelism), and sophisticated delivery semantics.
But the core pattern remains the same: publishers and subscribers communicate through topics, with a broker managing the complexity in between, and backpressure ensuring the system doesn't overwhelm itself.

[rabbitmq]: https://www.rabbitmq.com/
[kafka]: https://kafka.apache.org/
[amazon-sqs]: https://aws.amazon.com/sqs/
