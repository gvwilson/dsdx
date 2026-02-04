"""Simulation demonstrating behavior during network partition."""

from asimpy import Environment
from storage_node import StorageNode
from partitioned_coordinator import PartitionedCoordinator
from kv_client import KVClient


def run_partition_simulation():
    """Demonstrate behavior during network partition."""
    env = Environment()

    nodes = [StorageNode(env, f"Node{i + 1}") for i in range(5)]
    coordinator = PartitionedCoordinator(
        env, nodes, replication_factor=3, read_quorum=2, write_quorum=2
    )

    # Initial write
    KVClient(
        env,
        "Client1",
        coordinator,
        [
            ("write", "status", "healthy"),
            ("read", "status", None),
        ],
    )

    # Cause a partition
    async def create_partition():
        await env.timeout(2.0)
        coordinator.partition_node("Node3")

        # Client still succeeds with remaining nodes
        await env.timeout(1.0)
        KVClient(
            env,
            "Client2",
            coordinator,
            [
                ("write", "status", "degraded"),
                ("read", "status", None),
            ],
        )

        # Heal partition
        await env.timeout(2.0)
        coordinator.heal_partition("Node3")

    env.process(create_partition())
    env.run(until=10)


if __name__ == "__main__":
    run_partition_simulation()
