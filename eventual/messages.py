"""Request and response message types for the key-value store."""

from dataclasses import dataclass
from typing import Optional, Any, List
from asimpy import Queue
from vector_clock import VectorClock
from versioned_value import VersionedValue


@dataclass
class ReadRequest:
    """Request to read a key."""

    key: str
    client_id: str
    response_queue: Queue


@dataclass
class WriteRequest:
    """Request to write a key."""

    key: str
    value: Any
    context: Optional[VectorClock]  # Client's version context
    client_id: str
    response_queue: Queue


@dataclass
class ReadResponse:
    """Response to a read request."""

    key: str
    versions: List[VersionedValue]  # May have multiple concurrent versions


@dataclass
class WriteResponse:
    """Response to a write request."""

    key: str
    success: bool
    clock: VectorClock
