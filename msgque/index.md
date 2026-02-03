# A Message Queue with Publish-Subscribe

Real-world distributed systems need a way for components to communicate without being tightly coupled.
When a web server processes an order, it might need to notify the inventory system, trigger an email, update analytics, and log the transaction.
If the web server called each of these services directly, a failure in any one would block the entire operation.
This is where message queues come in.

Systems like RabbitMQ, Apache Kafka, and Amazon SQS act as intermediaries that decouple message producers from consumers.
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

```python
@dataclass
class Message:
    """A message sent through the queue system."""
    topic: str
    content: str
    id: int
    timestamp: float
```

The `Message` class represents data flowing through our system.
Each message has a topic (like "orders" or "user-activity"), content (the actual data), a unique ID, and a timestamp.
In a real system, messages would contain rich structured data, but strings are sufficient for our example.

```python
class MessageBroker:
    """A message broker that routes messages to topic subscribers."""
    
    def __init__(self, env: Environment, buffer_size: int = 100):
        self.env = env
        self.buffer_size = buffer_size
        # Topics map to lists of subscriber queues
        self.topics: Dict[str, List[Queue]] = defaultdict(list)
        # Statistics for observability
        self.messages_published = 0
        self.messages_delivered = 0
        
    def subscribe(self, topic: str) -> Queue:
        """Create a queue for a subscriber to a topic."""
        queue = Queue(self.env)
        self.topics[topic].append(queue)
        return queue
    
    async def publish(self, message: Message):
        """Publish a message to all subscribers of its topic."""
        self.messages_published += 1
        
        # Find all subscriber queues for this topic
        queues = self.topics.get(message.topic, [])
        
        if not queues:
            print(f"[{self.env.now:.1f}] No subscribers for topic '{message.topic}'")
            return
        
        # Deliver to each subscriber's queue
        for queue in queues:
            await queue.put(message)
            self.messages_delivered += 1
```

The broker maintains a dictionary mapping topics to lists of queues.
When a message is published, the broker looks up the topic and places the message in each subscriber's queue.
Using separate queues per subscriber ensures that a slow consumer doesn't block others—this is a key property of the pattern.

Unlike many message queue implementations that would drop messages when queues fill up, our asimpy queues grow unbounded.
In a real system, you'd want to enforce limits and implement backpressure or message dropping policies.
We'll discuss delivery semantics later.

Now let's implement publishers.
A publisher sends messages to topics at some rate:

```python
class Publisher(Process):
    """Publishes messages to topics."""
    
    def init(self, broker: MessageBroker, name: str, topic: str, interval: float):
        self.broker = broker
        self.name = name
        self.topic = topic
        self.interval = interval
        self.message_counter = 0
        
    async def run(self):
        """Generate and publish messages."""
        while True:
            # Create a message
            self.message_counter += 1
            message = Message(
                topic=self.topic,
                content=f"Message {self.message_counter} from {self.name}",
                id=self.message_counter,
                timestamp=self.now
            )
            
            # Publish it
            print(f"[{self.now:.1f}] {self.name} publishing: {message.content}")
            await self.broker.publish(message)
            
            # Wait before next message
            await self.timeout(self.interval)
```

This publisher sends messages at regular intervals.
Real publishers would react to external events (like HTTP requests or database changes), but timed generation works well for simulation.
The `await self.timeout()` pauses this process and resumes after the specified time.

Notice that we inherit from `Process`, which is asimpy's base class for active components.
The `init()` method is called during construction to set up our state, and `run()` is the coroutine that defines the publisher's behavior.

Finally, subscribers receive and process messages:

```python
class Subscriber(Process):
    """Subscribes to topics and processes messages."""
    
    def init(self, broker: MessageBroker, name: str, topics: List[str], 
             processing_time: float):
        self.broker = broker
        self.name = name
        self.topics = topics
        self.processing_time = processing_time
        self.messages_received = 0
        
        # Subscribe to all topics and get a queue for each
        self.queues = {}
        for topic in topics:
            queue = broker.subscribe(topic)
            self.queues[topic] = queue
    
    async def run(self):
        """Process messages from subscribed topics."""
        while True:
            # Wait for a message from any queue
            # Build a dict of topic -> get() coroutines
            get_operations = {
                topic: queue.get() 
                for topic, queue in self.queues.items()
            }
            
            # Wait for the first one to complete
            topic, message = await FirstOf(self._env, **get_operations)
            
            self.messages_received += 1
            latency = self.now - message.timestamp
            
            print(f"[{self.now:.1f}] {self.name} received from '{topic}': "
                  f"{message.content} (latency: {latency:.1f})")
            
            # Simulate processing time
            await self.timeout(self.processing_time)
```

The subscriber uses asimpy's `FirstOf` to wait on multiple queues simultaneously—whichever queue has a message first will complete.
This is more elegant than round-robin polling.
Real implementations use event-driven APIs or threads, but `FirstOf` captures the same semantics: we wait for any subscribed topic to produce a message.

The key point is that processing happens asynchronously: the subscriber takes messages from its queues and processes them at its own pace, independently of the publishers and other subscribers.

## Running a Simulation

Let's create a scenario with multiple publishers and subscribers to see the system in action:

```python
def run_simulation():
    """Run a simulation of the message queue system."""
    env = Environment()
    broker = MessageBroker(env, buffer_size=10)
    
    # Create publishers
    order_pub = Publisher(env, broker, "OrderService", "orders", interval=2.0)
    user_pub = Publisher(env, broker, "UserService", "user-activity", interval=1.5)
    
    # Create subscribers
    # Fast subscriber handling orders
    inventory = Subscriber(env, broker, "Inventory", ["orders"], 
                          processing_time=0.5)
    
    # Slow subscriber handling orders
    email = Subscriber(env, broker, "Email", ["orders"], 
                      processing_time=3.0)
    
    # Subscriber handling multiple topics
    analytics = Subscriber(env, broker, "Analytics", 
                          ["orders", "user-activity"], 
                          processing_time=1.0)
    
    # Run simulation
    env.run(until=20)
    
    # Print statistics
    print("\n=== Statistics ===")
    print(f"Messages published: {broker.messages_published}")
    print(f"Messages delivered: {broker.messages_delivered}")
    print(f"Inventory received: {inventory.messages_received}")
    print(f"Email received: {email.messages_received}")
    print(f"Analytics received: {analytics.messages_received}")

if __name__ == "__main__":
    run_simulation()
```

When you run this code, you'll see messages being published and consumed asynchronously.
Notice how the fast Inventory service keeps up with orders, while the slow Email service falls behind.
Messages queue up waiting for processing—this is the buffering we mentioned earlier.

The Analytics service receives messages from multiple topics, demonstrating how subscribers can aggregate different event streams.
This is common in real systems: a data warehouse might subscribe to dozens of topics to build a complete picture of system activity.

## Delivery Guarantees

Our implementation provides unbounded queuing, which means messages are never dropped (assuming infinite memory).
This is closer to "at-least-once" delivery, though we haven't implemented acknowledgments or redelivery on failure.
Let's discuss the spectrum of delivery guarantees:

**At-most-once delivery** ensures that messages are delivered zero or one time—never duplicated, but possibly lost.
This is achieved by dropping messages when queues are full or when subscribers are unavailable.
It's the weakest guarantee but the simplest to implement and the fastest.

**At-least-once delivery** ensures every message is delivered, possibly multiple times.
This requires acknowledgments: the broker keeps messages until subscribers confirm receipt.
If a subscriber crashes before acknowledging, the broker redelivers to another subscriber or retries.
Kafka and RabbitMQ support this mode.

**Exactly-once delivery** is the strongest guarantee: each message is processed exactly once.
This is surprisingly difficult in distributed systems due to failures and network issues.
Kafka achieves this through idempotent producers and transactional consumers—essentially assigning each message a unique ID and having consumers track which IDs they've processed.

Here's how we could extend our broker to support at-least-once delivery with acknowledgments:

```python
class AckMessage(Message):
    """Message that requires acknowledgment."""
    ack_id: int = 0

class AckBroker(MessageBroker):
    """Broker with acknowledgment support."""
    
    def __init__(self, env: Environment, buffer_size: int = 100, 
                 ack_timeout: float = 10.0):
        super().__init__(env, buffer_size)
        self.ack_timeout = ack_timeout
        self.pending_acks = {}  # ack_id -> (message, timestamp, queue)
        self.next_ack_id = 0
    
    async def publish(self, message: Message):
        """Publish with ack tracking."""
        queues = self.topics.get(message.topic, [])
        
        for queue in queues:
            ack_id = self.next_ack_id
            self.next_ack_id += 1
            
            ack_msg = AckMessage(
                topic=message.topic,
                content=message.content,
                id=message.id,
                timestamp=message.timestamp,
                ack_id=ack_id
            )
            
            self.pending_acks[ack_id] = (ack_msg, self.env.now, queue)
            await queue.put(ack_msg)
            
            # Schedule redelivery if not acked
            self.env.schedule(
                self.env.now + self.ack_timeout,
                lambda aid=ack_id: self._check_ack(aid)
            )
    
    def acknowledge(self, ack_id: int):
        """Acknowledge receipt of a message."""
        if ack_id in self.pending_acks:
            del self.pending_acks[ack_id]
    
    async def _check_ack(self, ack_id: int):
        """Redeliver if not acknowledged."""
        if ack_id in self.pending_acks:
            msg, original_time, queue = self.pending_acks[ack_id]
            print(f"[{self.env.now:.1f}] Redelivering {msg.content} "
                  f"(ack_id {ack_id})")
            await queue.put(msg)
```

A subscriber using this broker would call `broker.acknowledge(message.ack_id)` after successfully processing each message.
Messages not acknowledged within the timeout would be redelivered.

## Consumer Groups and Load Balancing

In production systems, we often want multiple instances of the same subscriber type to share the workload.
This is called a consumer group: messages on a topic are distributed among group members rather than duplicated to each.
Here's a simple implementation:

```python
class ConsumerGroup:
    """Distribute messages among multiple consumers."""
    
    def __init__(self, env: Environment, broker: MessageBroker, 
                 topic: str, num_consumers: int):
        self.env = env
        self.queue = broker.subscribe(topic)
        self.consumers = []
        
        # Create consumer queues for load balancing
        for i in range(num_consumers):
            consumer_queue = Queue(env)
            self.consumers.append(consumer_queue)
        
        # Start distributor process
        self._distributor = _Distributor(env, self.queue, self.consumers)
    
    def get_consumer_queue(self, index: int) -> Queue:
        """Get queue for a specific consumer in the group."""
        return self.consumers[index]

class _Distributor(Process):
    """Distribute messages round-robin to consumers."""
    
    def init(self, source: Queue, destinations: List[Queue]):
        self.source = source
        self.destinations = destinations
        self.next_dest = 0
    
    async def run(self):
        """Forward messages to consumers in round-robin order."""
        while True:
            message = await self.source.get()
            dest = self.destinations[self.next_dest]
            await dest.put(message)
            self.next_dest = (self.next_dest + 1) % len(self.destinations)
```

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
