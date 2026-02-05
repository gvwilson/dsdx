"""OAuth 2.0 Resource Server implementation."""

from asimpy import Process, Queue
from oauth_types import ResourceRequest, ResourceResponse
from authorization_server import AuthorizationServer


class ResourceServer(Process):
    """OAuth 2.0 resource server (protected API)."""

    def init(self, auth_server: AuthorizationServer):
        self.auth_server = auth_server
        self.resource_queue = Queue(self._env)

        # Protected resources
        self.resources = {
            "/api/profile": {
                "scope_required": ["profile"],
                "data": {"name": "Alice", "email": "alice@example.com"},
            },
            "/api/photos": {
                "scope_required": ["photos"],
                "data": {"photos": ["photo1.jpg", "photo2.jpg", "photo3.jpg"]},
            },
            "/api/messages": {
                "scope_required": ["messages"],
                "data": {"messages": ["Hello!", "How are you?"]},
            },
        }

        print(f"[{self.now:.1f}] Resource Server started")

    async def run(self):
        """Main server loop."""
        while True:
            request = await self.resource_queue.get()
            await self.handle_resource_request(request)

    async def handle_resource_request(self, request: ResourceRequest):
        """Handle API request with access token."""
        print(f"[{self.now:.1f}] ResourceServer: Received {request}")

        # Validate access token
        if request.access_token not in self.auth_server.access_tokens:
            print(f"[{self.now:.1f}] ResourceServer: Invalid token")
            await request.response_queue.put(
                ResourceResponse(success=False, error="invalid_token")
            )
            return

        token = self.auth_server.access_tokens[request.access_token]

        if not token.is_valid(self.now):
            print(f"[{self.now:.1f}] ResourceServer: Token expired")
            await request.response_queue.put(
                ResourceResponse(success=False, error="token_expired")
            )
            return

        # Check resource exists
        if request.resource_path not in self.resources:
            print(f"[{self.now:.1f}] ResourceServer: Resource not found")
            await request.response_queue.put(
                ResourceResponse(success=False, error="not_found")
            )
            return

        # Check token has required scope
        resource = self.resources[request.resource_path]
        required_scopes = set(resource["scope_required"])
        token_scopes = set(token.scope)

        if not required_scopes.issubset(token_scopes):
            print(f"[{self.now:.1f}] ResourceServer: Insufficient scope")
            await request.response_queue.put(
                ResourceResponse(success=False, error="insufficient_scope")
            )
            return

        # Return protected resource
        print(f"[{self.now:.1f}] ResourceServer: Returning {request.resource_path}")
        await request.response_queue.put(
            ResourceResponse(success=True, data=resource["data"])
        )
