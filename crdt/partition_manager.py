"""Manages network partitions between replicas."""

from asimpy import Process
from typing import List
from partitioned_crdt_replica import PartitionedCRDTReplica


class PartitionManager(Process):
    """Manages network partitions."""
    
    def init(self, replicas: List[PartitionedCRDTReplica]):
        self.replicas = replicas
    
    async def run(self):
        """Create and heal partitions."""
        # Create partition at time 2
        await self.timeout(2.0)
        self.replicas[0].partition_from(self.replicas[1].replica_id)
        self.replicas[1].partition_from(self.replicas[0].replica_id)
        
        # Heal partition at time 8
        await self.timeout(6.0)
        self.replicas[0].heal_partition(self.replicas[1].replica_id)
        self.replicas[1].heal_partition(self.replicas[0].replica_id)
