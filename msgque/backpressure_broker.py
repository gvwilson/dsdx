from asimpy import Environment, Queue
from collections import defaultdict

from message import Message


# mccole: backpressure
class BackpressureBroker:
    """A message broker with backpressure support."""

    def __init__(self, env: Environment, max_queue_size: int = 10):
        self.env = env
        self.max_queue_size = max_queue_size
        self.topics: dict[str, list[Queue]] = defaultdict(list)
        self.messages_published = 0
        self.messages_delivered = 0
        self.messages_dropped = 0

    def subscribe(self, topic: str) -> Queue:
        """Create a bounded queue for a subscriber to a topic."""
        queue = Queue(self.env, max_capacity=self.max_queue_size)
        self.topics[topic].append(queue)
        return queue

    async def publish(self, message: Message) -> bool:
        """Publish a message, applying backpressure if queues are full.

        Returns True if message was delivered to all subscribers,
        False if any queue was full and message was dropped.
        """
        self.messages_published += 1
        queues = self.topics.get(message.topic, [])

        all_delivered = True
        for queue in queues:
            if queue.is_full():
                # Queue is full - drop message for this subscriber
                self.messages_dropped += 1
                all_delivered = False
            else:
                await queue.put(message)
                self.messages_delivered += 1

        return all_delivered


# mccole: /backpressure
