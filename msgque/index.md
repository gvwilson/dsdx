# A Publish-Subscribe Message Queue

<p class="subtitle" markdown="1">loosely-coupled communication</p>

When a web server processes an order,
it might need to notify the inventory system,
trigger an email,
update analytics,
and log the transaction.
If the web server calls each of these services directly,
a failure in any one could block the entire operation.
This is where message queues come in.

Systems like [RabbitMQ][rabbitmq], [Apache Kafka][kafka], and [Amazon SQS][amazon-sqs]
decouple message producers from consumers.
A publisher sends messages to a named topic without knowing who (if anyone) will receive them.
Subscribers express interest in topics and then receive messages asynchronously,
processing them at their own pace.

This lesson shows how to build a message delivery service using
the [publish-subscribe pattern](g:publish-subscribe).
The [message broker](g:message-broker) keeps track of which subscribers are interested in which topics.
When a message arrives,
it delivers it to them.
This is called [fan-out](g:fan-out):
one message can reach many consumers.

Publish-subscribe is popular because
it [decouples](g:decoupling) publishers and subscribers.
They don't need to know about each other:
they only share knowledge of topic names,
which allows us to add more of either without modifying existing code.
In addition,
the broker provides [buffering](g:buffer):
if consumers are slow or temporarily unavailable,
messages wait rather than being lost.

## Our Implementation {: #msgque-impl}

Our first implementation has three main components:
publishers that send messages,
a broker that routes messages to topics,
and subscribers that receive and process messages.
We start by defining a [dataclass](g:dataclass) to store a single message:

<div data-inc="message.py" data-filter="inc=message"></div>

Each message belongs to a topic like "orders" or "user-activity",
and has some content, a unique ID, and a timestamp.
Messages in a real system would contain structured data (e.g., as [JSON](g:json)),
but strings are sufficient for our example.

The broker stores a dictionary called `topics` mapping topics to lists of queues:

<div data-inc="broker.py" data-filter="inc=broker"></div>

<div class="callout" markdown="1">

`MessageBroker` isn't an active `Process`,
but it needs the [asimpy][asimpy] `Environment` to construct `Queue` objects.
We have also given it counters to record the number of of messages published and delivered.

</div>

When someone wants to be notified of messages,
it registers itself and gets a queue in return:

<div data-inc="broker.py" data-filter="inc=subscribe"></div>

Using separate queues per subscriber ensures that a slow consumer doesn't block others,
which is a key property of the pattern.
Real-world message queue implementations would drop messages when queues fill up;
we will look at this later.

When a message is published,
the broker looks up the topic and places the message in each subscriber's queue:

<div data-inc="broker.py" data-filter="inc=publish"></div>

To test this,
let's create a publisher that sendss messages to a specific topic at some rate:

<div data-inc="publisher.py" data-filter="inc=publisher"></div>

Real publishers would react to external events (like HTTP requests or database changes),
but timed generation works well for simulation.

Notice that we inherit from `Process`, which is asimpy's base class for active components.
As described in [the appendix](@/asimpy/),
the `init()` method is called during construction to set up our state,
while `run()` creates the coroutine that defines the publisher's behavior.

Finally, our simulated subscribers receive and process messages:

<div data-inc="subscriber.py" data-filter="inc=subscriber"></div>

<div class="callout" markdown="1">

`Subscriber` uses [asimpy][asimpy]'s `FirstOf` to wait on multiple queues simultaneously.
Whichever queue has a message first will complete,
and all other requests will be canceled.
This is more elegant than [round-robin polling](g:round-robin-polling).
Real implementations use event-driven APIs or threads,
but `FirstOf` captures the same semantics.

</div>

## Running a Simulation {: #msgque-sim}

Let's create a scenario with multiple publishers and subscribers to see the system in action:

<div data-inc="ex_simple.py" data-filter="inc=simulate"></div>

The output shows being published and consumed asynchronously:

<div data-inc="ex_simple.txt" data-filter="head=10 + tail=6"></div>

Notice how the fast `Inventory` service keeps up with orders,
while the slow `Email` service falls behind:
this is the buffering we mentioned earlier.
At the same time,
the `Analytics` service receives messages from multiple topics,
demonstrating how subscribers can aggregate different event streams.

## Backpressure and Flow Control {: #msgque-back}

So far, our broker uses unbounded queues that grow indefinitely.
This works in simulation but fails in production:
if publishers produce faster than subscribers consume,
queues will eventually exhaust memory and crash the system.
The solution is [backpressure](g:backpressure):
a mechanism where slow consumers signal upstream components to slow down.
Backpressure is fundamental to building robust distributed systems.
Without it, a single slow consumer can cause cascading failures.

There are several strategies for implementing backpressure:

Bounded queues with blocking
:   Publishers block when queues are full, naturally slowing them down.
    This provides strong backpressure but can cause publishers to stall.

Bounded queues with dropping
:   When queues are full, new messages are dropped.
    This keeps the system running but loses data.
    This strategy is usually combined with metric collection and reporting
    so that operators know data is being lost.

Adaptive rate limiting
:   Publishers monitor queue sizes or delivery failures and dynamically adjust their publishing rate.
    This is more complex but provides smoother behavior under heavy load.

Priority-based dropping
:   When backpressure occurs, the system drops low-priority messages first
    in order to preserve critical data.

Let's implement bounded queues with message dropping and adaptive rate limiting.
The constructor takes an extra parameter `max_queue_size`:

<div data-inc="backpressure_broker.py" data-filter="inc=backpressure"></div>

It uses this value to initialize queues:

<div data-inc="backpressure_broker.py" data-filter="inc=subscribe"></div>

When a queue is full,
`publish()` drops the message for that subscriber
and returns `False` to signal backpressure to the publisher:

<div data-inc="backpressure_broker.py" data-filter="inc=publish"></div>

Now we need a publisher that responds to backpressure.
Its constructor needs two new parameters:
a base interval to wait before re-trying a message,
and a [backoff multiplier](g:backoff-multiplier)
that tells it how to increase the interval if repeated attempts to publish fail:

<div data-inc="backpressure_publisher.py" data-filter="inc=init"></div>

The publisher's `run()` method uses these two parameters to implement
[exponential backoff](g:exponential-backoff),
which is one of the most important concepts in distributed systems.
If an attempt to publish a message fails,
the publisher increases its interval between messages.
If publishing succeeds,
on the other hand,
it gradually reduces the interval back to the base rate.
This creates a [negative feedback loop](g:negative-feedback-loop) that stabilizes the system under load.

Let's see backpressure in action with one fast publisher,
one that's slow,
and and a deliberately small queue size:

<div data-inc="ex_backpressure.py" data-filter="inc=sim"></div>

The full output shows that the publisher starts fast
but encounter backpressure as the slow subscriber's queue fills.
The publisher adapts by slowing down,
and the system reaches equilibrium where the publishing rate matches the consumption rate.

<div data-inc="ex_backpressure.txt" data-filter="head=10 + tail=7"></div>

## Message Priority {: #msgque-priority}

In most real systems, not all messages are equal.
As the system becomes overloaded,
we might want to preserve high-priority messages while dropping low-priority ones.
To implement this,
we start by adding a `priority` field to our messages:

<div data-inc="priority_backpressure.py" data-filter="inc=message"></div>

When we publish a message,
we check queue-by-queue to see if there's room.
If not,
we either evict a lower-priority message or discard the one that just arrived:

<div data-inc="priority_backpressure.py" data-filter="inc=publish"></div>

A full implementation would maintain a [priority queue](g:priority-queue)
to allow efficient eviction of low-priority messages.
We will explore this in the exercises.

## Delivery Guarantees {: #msgque-delivery}

Different message delivery systems provide different kinds of delivery guarantees:

At-most-once delivery
:   This ensures that messages are delivered zero or one times,
    i.e., are never duplicated, but possibly lost.
    This is achieved by dropping messages when queues are full or when subscribers are unavailable.
    It's the weakest guarantee but the simplest and fastest to implement.

At-least-once delivery
:   This ensures every message is delivered, possibly multiple times.
    It acknowledgments: the broker keeps messages until subscribers confirm receipt.
    If a subscriber crashes before acknowledging,
    the broker redelivers to another subscriber or retries.

Exactly-once delivery
:   This is the strongest guarantee: each message is processed exactly once.
    It is surprisingly difficult to achieve in distributed systems due to failures and network issues.

We can extend our broker to support at-least-once delivery with acknowledgments.
First,
we add an acknowledgment ID field to each message:

<div data-inc="ack_broker.py" data-filter="inc=ackmessage"></div>

Next,
we have the broker keep track of how long to wait for acknowledgments
and of outstanding acknowledgments:

<div data-inc="ack_broker.py" data-filter="inc=broker"></div>

When it publishes a message,
it adds a note to wait for an acknowledgment:

<div data-inc="ack_broker.py" data-filter="inc=publish"></div>

A subscriber using this broker calls `broker.acknowledge(message.ack_id)`
after successfully processing a message.
Messages not acknowledged within the timeout are redelivered.

## Consumer Groups and Load Balancing {: #msgque-balance}

In production systems,
multiple instances of the same subscriber type often share the workload.
This is called a [consumer group](g:consumer-group):
messages on a topic are distributed among group members rather than duplicated to each.
Here's a simple implementation:

<div data-inc="consumer_group.py" data-filter="inc=consumer"></div>

It relies on an internal `_Distributor` process to do the work:

<div data-inc="consumer_group.py" data-filter="inc=distributor"></div>

This consumer group receives messages from the broker on a single queue,
then distributes them round-robin to individual consumers' queues.
Each consumer in the group processes a subset of the messages in parallel with its peers.
Real systems use more sophisticated load balancing algorithms,
such as weighted distribution,
least-loaded routing,
or partition-based assignment.

## Summary {: #msgque-summary}

1.  The publish-subscribe pattern decouples system components,
    enabling independent scaling and evolution.

1.  Routing messages through a broker enables buffering,
    fan-out,
    and fault tolerance.

1.  Backpressure ensures the system prevents cascading failures
    when consumers can't keep up with producers.

## Exercises {: #msgque-exercises}

FIXME: add exercises.

[rabbitmq]: https://www.rabbitmq.com/
[kafka]: https://kafka.apache.org/
[amazon-sqs]: https://aws.amazon.com/sqs/
