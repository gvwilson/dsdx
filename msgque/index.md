# A Message Queue with Publish-Subscribe

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

<div data-inc="simulate.py" data-filter="inc=simulate"></div>

When we run this code, we see messages being published and consumed asynchronously.
Notice how the fast `Inventory` service keeps up with orders, while the slow `Email` service falls behind.
Messages queue up waiting for processing—this is the buffering we mentioned earlier.

The `Analytics` service receives messages from multiple topics,
demonstrating how subscribers can aggregate different event streams.
This is common in real systems: a data warehouse might subscribe to dozens of topics to build a complete picture of system activity.

## Delivery Guarantees

Our implementation provides unbounded queuing, which means messages are never dropped (assuming infinite memory).
This is closer to "at-least-once" delivery, though we haven't implemented acknowledgments or redelivery on failure.
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
The pattern appears throughout modern architectures: microservices use it for inter-service communication, frontend applications use it for real-time updates, and data pipelines use it for stream processing.

The code we've written captures the essential ideas: topics, subscriptions, asynchronous delivery, and queuing.
We've seen how asimpy's async/await syntax makes concurrent behavior natural to express, and how `FirstOf` enables waiting on multiple message sources simultaneously.
Real systems add persistence (writing messages to disk), replication (for fault tolerance), partitioning (for parallelism), and sophisticated delivery semantics.
But the core pattern remains the same: publishers and subscribers communicate through topics, with a broker managing the complexity in between.
