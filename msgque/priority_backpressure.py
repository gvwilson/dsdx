from dataclasses import dataclass
from asimpy import Environment, Queue
from collections import defaultdict

from message import Message


# mccole: message
@dataclass
class PriorityMessage(Message):
    priority: int = 0  # Higher number = higher priority
# mccole: /message


class PriorityBackpressureBroker:
    """Broker that drops low-priority messages first under backpressure."""

    def __init__(self, env: Environment, max_queue_size: int = 10):
        self.env = env
        self.max_queue_size = max_queue_size
        self.topics: dict[str, list[Queue]] = defaultdict(list)
        self.num_published = 0
        self.num_delivered = 0
        self.num_dropped = 0
        self.dropped_by_priority: dict[int, int] = defaultdict(int)

    def subscribe(self, topic: str) -> Queue:
        """Create a bounded queue for a subscriber to a topic."""
        queue = Queue(self.env, max_capacity=self.max_queue_size)
        self.topics[topic].append(queue)
        return queue

    # mccole: publish
    async def publish(self, message: PriorityMessage) -> bool:
        """Publish with priority-based backpressure handling."""
        self.num_published += 1
        queues = self.topics.get(message.topic, [])

        all_delivered = True
        for queue in queues:
            if queue.is_full():
                # Queue full - check if we should drop this message
                # or evict a lower-priority one
                if await self._try_evict_lower_priority(queue, message):
                    await queue.put(message)
                    self.num_delivered += 1
                else:
                    # Drop this message
                    self.num_dropped += 1
                    self.dropped_by_priority[message.priority] += 1
                    all_delivered = False
            else:
                await queue.put(message)
                self.num_delivered += 1

        return all_delivered
    # mccole: /publish

    async def _try_evict_lower_priority(
        self, queue: Queue, new_message: PriorityMessage
    ) -> bool:
        """Return True if eviction succeeded, False otherwise."""
        if new_message.priority > 5:
            self.num_dropped += 1
            return True
        return False
