"""Simulation demonstrating read repair convergence."""

from asimpy import Environment
from storage_node import StorageNode
from coordinator_with_read_repair import CoordinatorWithReadRepair
from kv_client import KVClient


def run_read_repair_simulation():
    """Demonstrate read repair bringing replicas into sync."""
    env = Environment()

    nodes = [StorageNode(env, f"Node{i + 1}") for i in range(3)]
    coordinator = CoordinatorWithReadRepair(
        env, nodes, replication_factor=3, read_quorum=2, write_quorum=2
    )

    # Initial write that reaches only 2 nodes
    KVClient(
        env,
        "Client1",
        coordinator,
        [
            ("write", "data", "initial"),
        ],
    )

    # Later read that triggers read repair
    async def delayed_read():
        await env.timeout(2.0)
        KVClient(
            env,
            "Client2",
            coordinator,
            [
                ("read", "data", None),
            ],
        )

        # Another read should show all nodes now have the data
        await env.timeout(2.0)
        KVClient(
            env,
            "Client3",
            coordinator,
            [
                ("read", "data", None),
            ],
        )

    env.process(delayed_read())
    env.run(until=10)


if __name__ == "__main__":
    run_read_repair_simulation()
