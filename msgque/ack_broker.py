from dataclasses import dataclass
from asimpy import Environment
from message import Message
from broker import MessageBroker


@dataclass
class AckMessage(Message):
    """Message that requires acknowledgment."""

    ack_id: int = 0


class AckBroker(MessageBroker):
    """Broker with acknowledgment support."""

    def __init__(
        self, env: Environment, buffer_size: int = 100, ack_timeout: float = 10.0
    ):
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
                ack_id=ack_id,
            )

            self.pending_acks[ack_id] = (ack_msg, self.env.now, queue)
            await queue.put(ack_msg)

            # Schedule redelivery if not acked
            self.env.schedule(
                self.env.now + self.ack_timeout, lambda aid=ack_id: self._check_ack(aid)
            )

    def acknowledge(self, ack_id: int):
        """Acknowledge receipt of a message."""
        if ack_id in self.pending_acks:
            del self.pending_acks[ack_id]

    async def _check_ack(self, ack_id: int):
        """Redeliver if not acknowledged."""
        if ack_id in self.pending_acks:
            msg, original_time, queue = self.pending_acks[ack_id]
            print(f"[{self.env.now:.1f}] Redelivering {msg.content} (ack_id {ack_id})")
            await queue.put(msg)
