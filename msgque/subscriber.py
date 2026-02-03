from typing import TYPE_CHECKING
from asimpy import FirstOf, Process

if TYPE_CHECKING:
    from .broker import MessageBroker


class Subscriber(Process):
    """Subscribes to topics and processes messages."""

    def init(
        self,
        broker: "MessageBroker",
        name: str,
        topics: list[str],
        processing_time: float,
    ):
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
                topic: queue.get() for topic, queue in self.queues.items()
            }

            # Wait for the first one to complete
            topic, message = await FirstOf(self._env, **get_operations)

            self.messages_received += 1
            latency = self.now - message.timestamp

            print(
                f"[{self.now:.1f}] {self.name} received from '{topic}': "
                f"{message.content} (latency: {latency:.1f})"
            )

            # Simulate processing time
            await self.timeout(self.processing_time)
