"""CRDT replica with state synchronization."""

from asimpy import Process
from typing import List
from pncounter import PNCounter
from lwwregister import LWWRegister
from orset import ORSet


class CRDTReplica(Process):
    """A replica maintaining CRDT state and syncing with others."""

    def init(self, replica_id: str, sync_interval: float = 2.0):
        self.replica_id = replica_id
        self.sync_interval = sync_interval

        # Initialize CRDTs
        self.counter = PNCounter(replica_id)
        self.register = LWWRegister()
        self.orset = ORSet(replica_id)

        # Track other replicas for syncing
        self.other_replicas: List["CRDTReplica"] = []

        # Statistics
        self.updates_applied = 0
        self.syncs_sent = 0

    async def run(self):
        """Periodically sync with other replicas."""
        while True:
            await self.timeout(self.sync_interval)
            await self.sync_with_peers()

    def add_peer(self, replica: "CRDTReplica"):
        """Register another replica to sync with."""
        if replica not in self.other_replicas:
            self.other_replicas.append(replica)

    async def sync_with_peers(self):
        """Send state to all peers."""
        for peer in self.other_replicas:
            await self.send_state_to(peer)

    async def send_state_to(self, peer: "CRDTReplica"):
        """Send our CRDT state to a peer."""
        self.syncs_sent += 1

        # Copy our state to send
        counter_copy = self.counter.copy()
        register_copy = self.register.copy()
        set_copy = self.orset.copy()

        # Peer receives and merges
        peer.receive_state(counter_copy, register_copy, set_copy, self.replica_id)

    def receive_state(
        self, counter: PNCounter, register: LWWRegister, orset: ORSet, from_replica: str
    ):
        """Receive and merge state from another replica."""
        self.counter.merge(counter)
        self.register.merge(register)
        self.orset.merge(orset)

        print(f"[{self.now:.1f}] {self.replica_id}: Received state from {from_replica}")
        print(f"  Counter: {self.counter.value()}")
        print(f"  Register: {self.register.value}")
        print(f"  Set: {self.orset.value()}")

    def local_increment(self, amount: int = 1):
        """Locally increment the counter."""
        self.counter.increment(amount)
        self.updates_applied += 1
        print(
            f"[{self.now:.1f}] {self.replica_id}: Incremented by {amount} "
            f"-> {self.counter.value()}"
        )

    def local_decrement(self, amount: int = 1):
        """Locally decrement the counter."""
        self.counter.decrement(amount)
        self.updates_applied += 1
        print(
            f"[{self.now:.1f}] {self.replica_id}: Decremented by {amount} "
            f"-> {self.counter.value()}"
        )

    def local_set_register(self, value):
        """Locally set the register value."""
        self.register.set(value, self.now, self.replica_id)
        self.updates_applied += 1
        print(f"[{self.now:.1f}] {self.replica_id}: Set register to '{value}'")

    def local_add_to_set(self, element):
        """Locally add element to set."""
        self.orset.add(element)
        self.updates_applied += 1
        print(
            f"[{self.now:.1f}] {self.replica_id}: Added '{element}' to set "
            f"-> {self.orset.value()}"
        )

    def local_remove_from_set(self, element):
        """Locally remove element from set."""
        self.orset.remove(element)
        self.updates_applied += 1
        print(
            f"[{self.now:.1f}] {self.replica_id}: Removed '{element}' from set "
            f"-> {self.orset.value()}"
        )
