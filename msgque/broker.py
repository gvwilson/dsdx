from asimpy import Environment, Queue
from collections import defaultdict

from message import Message


class MessageBroker:
    """A message broker that routes messages to topic subscribers."""

    def __init__(self, env: Environment, buffer_size: int = 100):
        self.env = env
        self.buffer_size = buffer_size

        # Topics map to lists of subscriber queues
        self.topics: dict[str, list[Queue]] = defaultdict(list)

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
