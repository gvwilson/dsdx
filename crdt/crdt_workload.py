"""Workload generator for CRDT operations."""

from asimpy import Process
from typing import List
from crdt_replica import CRDTReplica


class CRDTWorkload(Process):
    """Generate CRDT operations on a replica."""

    def init(self, replica: CRDTReplica, operations: List[tuple]):
        self.replica = replica
        self.operations = operations

    async def run(self):
        """Execute operations with delays."""
        for op_type, *args in self.operations:
            if op_type == "wait":
                await self.timeout(args[0])
            elif op_type == "increment":
                self.replica.local_increment(args[0] if args else 1)
            elif op_type == "decrement":
                self.replica.local_decrement(args[0] if args else 1)
            elif op_type == "set":
                self.replica.local_set_register(args[0])
            elif op_type == "add":
                self.replica.local_add_to_set(args[0])
            elif op_type == "remove":
                self.replica.local_remove_from_set(args[0])

            # Small delay between operations
            await self.timeout(0.1)
