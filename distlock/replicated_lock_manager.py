# replicated_lock_manager.py
"""Replicated lock manager with majority voting."""

from asimpy import Environment, Queue
from typing import Optional
from basic_lock_server import LockServer, LockRequest


class ReplicatedLockManager:
    """Manages multiple lock servers with majority voting."""

    def __init__(
        self, env: Environment, num_servers: int = 3, lease_duration: float = 5.0
    ):
        self.env = env
        self.servers = []

        for i in range(num_servers):
            server = LockServer(env, f"Server{i + 1}", lease_duration)
            self.servers.append(server)

        self.majority = (num_servers // 2) + 1

    async def acquire_lock(self, client_id: str, resource: str) -> Optional[int]:
        """Try to acquire lock from majority of servers."""
        responses = []
        response_queues = []

        # Send request to all servers
        for server in self.servers:
            response_queue = Queue(self.env)
            response_queues.append(response_queue)

            request = LockRequest(
                client_id=client_id,
                resource=resource,
                operation="acquire",
                response_queue=response_queue,
            )
            await server.request_queue.put(request)

        # Collect responses
        for queue in response_queues:
            response = await queue.get()
            responses.append(response)

        # Check if we got majority approval
        successful = [r for r in responses if r.success]

        if len(successful) >= self.majority:
            # Use the highest token from successful responses
            token = max(r.token for r in successful)
            print(
                f"[{self.env.now:.1f}] Lock acquired by {client_id} "
                f"({len(successful)}/{len(self.servers)} servers, token {token})"
            )
            return token
        else:
            print(
                f"[{self.env.now:.1f}] Lock acquisition failed for {client_id} "
                f"({len(successful)}/{len(self.servers)} servers)"
            )
            return None

    async def release_lock(self, client_id: str, resource: str):
        """Release lock from all servers."""
        for server in self.servers:
            response_queue = Queue(self.env)
            request = LockRequest(
                client_id=client_id,
                resource=resource,
                operation="release",
                response_queue=response_queue,
            )
            await server.request_queue.put(request)
            await response_queue.get()
