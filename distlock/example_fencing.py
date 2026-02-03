# example_fencing.py
"""Demonstration of fencing tokens preventing split-brain."""

from asimpy import Environment
from basic_lock_server import LockServer
from protected_resource import ProtectedResource
from fenced_client import FencedClient


def run_fencing_simulation():
    """Demonstrate fencing tokens preventing split-brain."""
    env = Environment()

    server = LockServer(env, "Server1", lease_duration=3.0)
    resource = ProtectedResource(env, "Database")

    # Client that will pause long enough for lease to expire
    FencedClient(
        env,
        "Client1",
        server,
        "db_lock",
        resource,
        work_duration=2.0,
        pause_duration=5.0,
    )

    # Client that acquires lock after client1's lease expires
    FencedClient(
        env,
        "Client2",
        server,
        "db_lock",
        resource,
        work_duration=2.0,
        pause_duration=0,
        initial_delay=4.0,
    )

    env.run(until=15)


if __name__ == "__main__":
    run_fencing_simulation()
