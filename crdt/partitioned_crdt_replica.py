"""CRDT replica with network partition support."""

from typing import Set
from crdt_replica import CRDTReplica


class PartitionedCRDTReplica(CRDTReplica):
    """CRDT replica that can be partitioned."""
    
    def init(self, replica_id: str, sync_interval: float = 2.0):
        super().init(replica_id, sync_interval)
        self.partitioned_from: Set[str] = set()
    
    def partition_from(self, replica_id: str):
        """Simulate network partition from another replica."""
        self.partitioned_from.add(replica_id)
        print(f"[{self.now:.1f}] {self.replica_id}: Partitioned from {replica_id}")
    
    def heal_partition(self, replica_id: str):
        """Heal network partition."""
        self.partitioned_from.discard(replica_id)
        print(f"[{self.now:.1f}] {self.replica_id}: Healed partition with {replica_id}")
    
    async def send_state_to(self, peer: 'CRDTReplica'):
        """Send state only if not partitioned."""
        if peer.replica_id in self.partitioned_from:
            return  # Network partition, can't send
        
        await super().send_state_to(peer)
