from asimpy import Environment, Queue
from collections import defaultdict

from message import Message


# mccole: broker
class MessageBroker:
    """A message broker that routes messages to topic subscribers."""

    def __init__(self, env: Environment, buffer_size: int = 100):
        self.env = env
        self.buffer_size = buffer_size
        self.topics: dict[str, list[Queue]] = defaultdict(list)
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
        queues = self.topics.get(message.topic, [])
        for queue in queues:
            await queue.put(message)
            self.messages_delivered += 1


# mccole: /broker
