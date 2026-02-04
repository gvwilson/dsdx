# Message Queue with Publish-Subscribe Pattern

Implementation of a message queue system with publish-subscribe pattern, based on
systems like RabbitMQ, Apache Kafka, and Amazon SQS.

## Overview

This chapter demonstrates how message brokers decouple producers from consumers,
enabling scalable fan-out communication and buffering to handle variable processing
speeds. The implementation shows the fundamental patterns used in event-driven
architectures throughout the industry.

## Files

### Core Components

- `basic_message_queue.py` - Complete working example with publishers, broker, and subscribers
- `ack_broker.py` - Extension showing at-least-once delivery with acknowledgments
- `consumer_group.py` - Extension showing consumer groups for load balancing

## Key Concepts

### Publish-Subscribe Pattern

Publishers send messages to topics without knowing who will receive them. Subscribers
express interest in topics and receive messages asynchronously. This provides:

- **Decoupling**: Publishers and subscribers don't know about each other
- **Fan-out**: One message reaches multiple subscribers
- **Buffering**: Queues absorb speed differences between producers and consumers
- **Scalability**: Add publishers/subscribers independently

### Delivery Guarantees

**At-most-once**: Messages delivered zero or one time (may be lost, never duplicated)
- Simplest implementation
- Lowest overhead
- Acceptable for metrics, logs

**At-least-once**: Messages always delivered (may be duplicated)
- Requires acknowledgments
- Broker retries on failure
- Used in RabbitMQ, Kafka

**Exactly-once**: Messages processed exactly once (most expensive)
- Requires idempotent processing or deduplication
- Kafka achieves this with transactions
- Hardest to implement correctly

### Architecture

```
Publisher         Broker           Subscribers
    |               |               |
    |--publish----->|               |
    |               |--deliver----->| (Subscriber 1)
    |               |--deliver----->| (Subscriber 2)
    |               |--deliver----->| (Subscriber 3)
```

## Real-World Applications

- **LinkedIn data pipeline**: Billions of events daily through Kafka
- **Netflix recommendations**: React to viewing patterns via message streams
- **Microservices**: Inter-service communication without tight coupling
- **Real-time analytics**: Aggregate clickstream data as it arrives
- **Event sourcing**: Store system state as a sequence of events

## Running the Examples

### Basic Example

```bash
python basic_message_queue.py
```

Shows publishers sending to topics, broker routing messages, and subscribers
receiving asynchronously. Demonstrates fan-out and buffering.

### Acknowledgment-Based Delivery

The `ack_broker.py` file shows how to implement at-least-once delivery by
tracking unacknowledged messages and redelivering on timeout.

### Consumer Groups

The `consumer_group.py` file demonstrates load balancing: messages are
distributed among group members rather than duplicated to each.

## Design Patterns

### Message Broker

Maintains topic subscriptions and routes messages to interested subscribers.
Each subscriber gets its own queue to prevent slow consumers from blocking
fast ones.

### Asynchronous Processing

Subscribers process messages at their own pace. Fast subscribers keep up in
real-time; slow subscribers fall behind but messages are buffered.

### Multi-Topic Subscription

A single subscriber can listen to multiple topics, aggregating different
event streams. Example: analytics service subscribing to orders, user
activity, and inventory changes.

## Production Considerations

Real message queue systems need:

- **Persistence**: Write messages to disk for durability
- **Replication**: Multiple broker instances for fault tolerance
- **Partitioning**: Distribute topic partitions across brokers for scalability
- **Ordering guarantees**: Within-partition ordering (Kafka) or global ordering
- **Backpressure**: Prevent producers from overwhelming the system
- **Dead letter queues**: Handle messages that can't be processed
- **Message TTL**: Expire old messages to prevent unbounded growth

## Further Reading

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/getstarted.html)
- [Amazon SQS Documentation](https://aws.amazon.com/sqs/)
- [Enterprise Integration Patterns](https://www.enterpriseintegrationpatterns.com/)
