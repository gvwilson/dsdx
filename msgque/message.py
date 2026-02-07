from dataclasses import dataclass


# mccole: message
@dataclass
class Message:
    """A message sent through the queue system."""

    topic: str
    content: str
    id: int
    timestamp: float


# mccole: /message
