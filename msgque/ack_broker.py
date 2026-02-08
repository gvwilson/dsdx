from dataclasses import dataclass
from asimpy import Environment
from message import Message
from broker import MessageBroker


# mccole: message
@dataclass
class AckMessage(Message):
    ack_id: int = 0
# mccole: /message


# mccole: broker
class AckBroker(MessageBroker):
    """Broker with acknowledgment support."""

    def __init__(self, env: Environment, ack_timeout: float = 10.0):
        super().__init__(env)
        self.ack_timeout = ack_timeout
        self.pending_acks = {}
        self.next_ack_id = 0
# mccole: /broker

    # mccole: acknowledge
    def acknowledge(self, ack_id: int):
        """Acknowledge receipt of a message."""
        if ack_id in self.pending_acks:
            del self.pending_acks[ack_id]
    # mccole: /acknowledge

    # mccole: publish
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

            # Schedule re-delivery if not acknowledged.
            self.env.schedule(
                self.env.now + self.ack_timeout, lambda aid=ack_id: self._check_ack(aid)
            )

    async def _check_ack(self, ack_id: int):
        """Redeliver if not acknowledged."""
        if ack_id in self.pending_acks:
            msg, original_time, queue = self.pending_acks[ack_id]
            print(f"[{self.env.now:.1f}] Redelivering {msg.content} (ack_id {ack_id})")
            await queue.put(msg)
    # mccole: /publish
