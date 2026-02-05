"""OAuth 2.0 Authorization Server implementation."""

from asimpy import Process, Queue, FirstOf
from typing import Dict, List
from oauth_types import (
    AuthorizationRequest, AuthorizationResponse,
    TokenRequest, TokenResponse,
    AuthorizationCode, AccessToken, generate_token
)


class AuthorizationServer(Process):
    """OAuth 2.0 authorization server."""
    
    def init(self):
        self.auth_queue = Queue(self._env)
        self.token_queue = Queue(self._env)
        
        # Registered clients
        self.clients: Dict[str, Dict] = {}
        
        # Issued authorization codes
        self.auth_codes: Dict[str, AuthorizationCode] = {}
        
        # Issued access tokens
        self.access_tokens: Dict[str, AccessToken] = {}
        
        # User credentials (simplified - real systems use secure storage)
        self.users = {
            "alice@example.com": "password123",
            "bob@example.com": "secret456"
        }
        
        print(f"[{self.now:.1f}] Authorization Server started")
    
    def register_client(self, client_id: str, client_secret: str, 
                       redirect_uris: List[str]):
        """Register a new OAuth client."""
        self.clients[client_id] = {
            "secret": client_secret,
            "redirect_uris": redirect_uris
        }
        print(f"[{self.now:.1f}] Registered client: {client_id}")
    
    async def run(self):
        """Main server loop."""
        while True:
            # Handle both authorization and token requests
            name, request = await FirstOf(
                self._env,
                auth=self.auth_queue.get(),
                token=self.token_queue.get()
            )
            
            if name == "auth":
                await self.handle_authorization_request(request)
            elif name == "token":
                await self.handle_token_request(request)
    
    async def handle_authorization_request(self, request: AuthorizationRequest):
        """Handle authorization request from client."""
        print(f"[{self.now:.1f}] AuthServer: Received {request}")
        
        # Validate client and redirect URI
        if request.client_id not in self.clients:
            print(f"[{self.now:.1f}] AuthServer: Unknown client {request.client_id}")
            return
        
        client = self.clients[request.client_id]
        if request.redirect_uri not in client["redirect_uris"]:
            print(f"[{self.now:.1f}] AuthServer: Invalid redirect URI")
            return
        
        # Simulate user authentication and consent
        await self.timeout(0.5)  # User login time
        print(f"[{self.now:.1f}] AuthServer: User authenticated, showing consent")
        
        await self.timeout(0.3)  # User consent time
        print(f"[{self.now:.1f}] AuthServer: User granted permissions: {request.scope}")
        
        # Generate authorization code
        code = generate_token("code")
        auth_code = AuthorizationCode(
            code=code,
            client_id=request.client_id,
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            expires_at=self.now + 600  # 10 minute expiry
        )
        self.auth_codes[code] = auth_code
        
        # Send code to client
        response = AuthorizationResponse(code=code, state=request.state)
        await request.response_queue.put(response)
        
        print(f"[{self.now:.1f}] AuthServer: Issued authorization code")
    
    async def handle_token_request(self, request: TokenRequest):
        """Exchange authorization code for access token."""
        print(f"[{self.now:.1f}] AuthServer: Received {request}")
        
        # Validate client credentials
        if request.client_id not in self.clients:
            print(f"[{self.now:.1f}] AuthServer: Unknown client")
            await request.response_queue.put(
                TokenResponse(access_token="", token_type="error")
            )
            return
        
        client = self.clients[request.client_id]
        if client["secret"] != request.client_secret:
            print(f"[{self.now:.1f}] AuthServer: Invalid client secret")
            await request.response_queue.put(
                TokenResponse(access_token="", token_type="error")
            )
            return
        
        # Validate authorization code
        if request.code not in self.auth_codes:
            print(f"[{self.now:.1f}] AuthServer: Invalid authorization code")
            await request.response_queue.put(
                TokenResponse(access_token="", token_type="error")
            )
            return
        
        auth_code = self.auth_codes[request.code]
        
        if not auth_code.is_valid(self.now):
            print(f"[{self.now:.1f}] AuthServer: Authorization code expired or used")
            await request.response_queue.put(
                TokenResponse(access_token="", token_type="error")
            )
            return
        
        if auth_code.client_id != request.client_id:
            print(f"[{self.now:.1f}] AuthServer: Code issued to different client")
            await request.response_queue.put(
                TokenResponse(access_token="", token_type="error")
            )
            return
        
        if auth_code.redirect_uri != request.redirect_uri:
            print(f"[{self.now:.1f}] AuthServer: Redirect URI mismatch")
            await request.response_queue.put(
                TokenResponse(access_token="", token_type="error")
            )
            return
        
        # Mark code as used
        auth_code.used = True
        
        # Generate access token
        access_token = generate_token("access")
        token = AccessToken(
            token=access_token,
            client_id=request.client_id,
            scope=auth_code.scope,
            expires_at=self.now + 3600  # 1 hour expiry
        )
        self.access_tokens[access_token] = token
        
        # Issue token
        response = TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
            scope=auth_code.scope
        )
        await request.response_queue.put(response)
        
        print(f"[{self.now:.1f}] AuthServer: Issued access token")
