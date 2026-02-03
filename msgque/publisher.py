from typing import TYPE_CHECKING
from asimpy import Process
from message import Message

if TYPE_CHECKING:
    from .broker import MessageBroker


class Publisher(Process):
    """Publishes messages to topics."""

    def init(self, broker: "MessageBroker", name: str, topic: str, interval: float):
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
                timestamp=self.now,
            )

            # Publish it
            print(f"[{self.now:.1f}] {self.name} publishing: {message.content}")
            await self.broker.publish(message)

            # Wait before next message
            await self.timeout(self.interval)
