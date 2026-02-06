# OAuth

When you click "Sign in with Google" on a website, you're using OAuth. When a mobile app requests access to your Twitter timeline, that's OAuth too. This protocol has become the standard way for applications to access user data without ever seeing the user's password. Understanding OAuth is essential for modern web development—it powers single sign-on, API access control, and third-party integrations across the internet.

OAuth 2.0 solves a fundamental problem: how do you give a third-party application limited access to your account without sharing your credentials? Before OAuth, users had to give their username and password to every app, which created security nightmares. OAuth introduces the concept of **tokens**—time-limited credentials with specific scopes that can be revoked without changing your password.

This pattern appears everywhere: GitHub uses OAuth for app permissions, Spotify for playlist access, Slack for bot integrations, and AWS for service-to-service authentication. Whether you're building a web app, mobile app, or API, you'll encounter OAuth.

## The OAuth Dance

OAuth involves four parties working together:

1. **Resource Owner** (the user): Owns the data being accessed
2. **Client** (the third-party app): Wants to access the user's data
3. **Authorization Server**: Authenticates the user and issues tokens
4. **Resource Server** (the API): Hosts the protected resources

The authorization flow works like this:

1. **Client requests authorization**: App redirects user to authorization server
2. **User authenticates**: User logs in and grants permission
3. **Server issues authorization code**: One-time code sent to client
4. **Client exchanges code for token**: Client authenticates itself and gets access token
5. **Client accesses resources**: Uses token to call protected APIs

The key insight is separation: the client never sees the user's password, and the token has limited scope and lifetime. This makes OAuth both secure and flexible.

## Authorization Code Flow

The most common OAuth flow is the Authorization Code flow, designed for server-side applications:

```python
from asimpy import Environment, Process, Queue
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
import random
import string


def generate_token(prefix: str = "tok") -> str:
    """Generate a random token."""
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    return f"{prefix}_{random_part}"


@dataclass
class AuthorizationRequest:
    """Request for user authorization."""
    client_id: str
    redirect_uri: str
    scope: List[str]
    state: str  # CSRF protection
    response_queue: Queue
    
    def __str__(self):
        return f"AuthRequest(client={self.client_id}, scope={self.scope})"


@dataclass
class AuthorizationResponse:
    """Response with authorization code."""
    code: str
    state: str
    
    def __str__(self):
        return f"AuthResponse(code={self.code[:8]}...)"


@dataclass
class TokenRequest:
    """Request to exchange code for access token."""
    code: str
    client_id: str
    client_secret: str
    redirect_uri: str
    response_queue: Queue
    
    def __str__(self):
        return f"TokenRequest(client={self.client_id})"


@dataclass
class TokenResponse:
    """Response with access token."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[List[str]] = None
    
    def __str__(self):
        return f"TokenResponse(token={self.access_token[:8]}...)"


@dataclass
class ResourceRequest:
    """Request to access protected resource."""
    access_token: str
    resource_path: str
    response_queue: Queue
    
    def __str__(self):
        return f"ResourceRequest(path={self.resource_path})"


@dataclass
class ResourceResponse:
    """Response from resource server."""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    
    def __str__(self):
        if self.success:
            return f"ResourceResponse(success=True)"
        return f"ResourceResponse(error={self.error})"


@dataclass
class AuthorizationCode:
    """Authorization code with metadata."""
    code: str
    client_id: str
    redirect_uri: str
    scope: List[str]
    expires_at: float
    used: bool = False
    
    def is_valid(self, now: float) -> bool:
        """Check if code is still valid."""
        return not self.used and now < self.expires_at


@dataclass
class AccessToken:
    """Access token with metadata."""
    token: str
    client_id: str
    scope: List[str]
    expires_at: float
    
    def is_valid(self, now: float) -> bool:
        """Check if token is still valid."""
        return now < self.expires_at
```

These data structures represent the messages exchanged during OAuth flows. The authorization code is short-lived (typically 10 minutes), while access tokens last longer (often 1 hour).

## Authorization Server

The authorization server handles user authentication and token issuance:

```python
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
            from asimpy import FirstOf
            
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
```

The authorization server is the trust anchor of OAuth. It verifies the user's identity, obtains consent, and issues tokens with appropriate scopes.

## Resource Server

The resource server hosts the protected API:

```python
class ResourceServer(Process):
    """OAuth 2.0 resource server (protected API)."""
    
    def init(self, auth_server: AuthorizationServer):
        self.auth_server = auth_server
        self.resource_queue = Queue(self._env)
        
        # Protected resources
        self.resources = {
            "/api/profile": {
                "scope_required": ["profile"],
                "data": {"name": "Alice", "email": "alice@example.com"}
            },
            "/api/photos": {
                "scope_required": ["photos"],
                "data": {"photos": ["photo1.jpg", "photo2.jpg", "photo3.jpg"]}
            },
            "/api/messages": {
                "scope_required": ["messages"],
                "data": {"messages": ["Hello!", "How are you?"]}
            }
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
```

The resource server validates tokens and enforces scope-based access control. It doesn't need to know about users—only tokens and scopes.

## OAuth Client

The client orchestrates the authorization flow:

```python
class OAuthClient(Process):
    """OAuth 2.0 client application."""
    
    def init(self, client_id: str, client_secret: str, redirect_uri: str,
             auth_server: AuthorizationServer, resource_server: ResourceServer):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_server = auth_server
        self.resource_server = resource_server
        
        self.access_token: Optional[str] = None
        
        print(f"[{self.now:.1f}] Client '{client_id}' started")
    
    async def run(self):
        """Demonstrate complete OAuth flow."""
        # Step 1: Request authorization
        scopes = ["profile", "photos"]
        code = await self.request_authorization(scopes)
        
        if not code:
            print(f"[{self.now:.1f}] Client: Authorization failed")
            return
        
        # Step 2: Exchange code for token
        token_response = await self.exchange_code_for_token(code)
        
        if not token_response or token_response.token_type == "error":
            print(f"[{self.now:.1f}] Client: Token exchange failed")
            return
        
        self.access_token = token_response.access_token
        print(f"[{self.now:.1f}] Client: Got access token!")
        
        # Step 3: Access protected resources
        await self.timeout(0.5)
        await self.access_resource("/api/profile")
        
        await self.timeout(0.5)
        await self.access_resource("/api/photos")
        
        # Try accessing resource without permission
        await self.timeout(0.5)
        await self.access_resource("/api/messages")
    
    async def request_authorization(self, scopes: List[str]) -> Optional[str]:
        """Step 1: Request user authorization."""
        print(f"[{self.now:.1f}] Client: Requesting authorization for {scopes}")
        
        state = generate_token("state")  # CSRF protection
        response_queue = Queue(self._env)
        
        request = AuthorizationRequest(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=scopes,
            state=state,
            response_queue=response_queue
        )
        
        await self.auth_server.auth_queue.put(request)
        response = await response_queue.get()
        
        # Validate state to prevent CSRF
        if response.state != state:
            print(f"[{self.now:.1f}] Client: State mismatch - possible CSRF attack!")
            return None
        
        print(f"[{self.now:.1f}] Client: Received authorization code")
        return response.code
    
    async def exchange_code_for_token(self, code: str) -> Optional[TokenResponse]:
        """Step 2: Exchange authorization code for access token."""
        print(f"[{self.now:.1f}] Client: Exchanging code for token")
        
        response_queue = Queue(self._env)
        
        request = TokenRequest(
            code=code,
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            response_queue=response_queue
        )
        
        await self.auth_server.token_queue.put(request)
        response = await response_queue.get()
        
        return response
    
    async def access_resource(self, path: str):
        """Step 3: Access protected resource with token."""
        print(f"[{self.now:.1f}] Client: Accessing {path}")
        
        if not self.access_token:
            print(f"[{self.now:.1f}] Client: No access token!")
            return
        
        response_queue = Queue(self._env)
        
        request = ResourceRequest(
            access_token=self.access_token,
            resource_path=path,
            response_queue=response_queue
        )
        
        await self.resource_server.resource_queue.put(request)
        response = await response_queue.get()
        
        if response.success:
            print(f"[{self.now:.1f}] Client: Success! Data: {response.data}")
        else:
            print(f"[{self.now:.1f}] Client: Failed - {response.error}")
```

The client never sees the user's password. It gets an authorization code, exchanges it for a token, and uses the token to access APIs.

## Basic OAuth Simulation

Let's see the complete flow in action:

```python
def run_basic_oauth_flow():
    """Demonstrate basic OAuth 2.0 authorization code flow."""
    env = Environment()
    
    # Create authorization server
    auth_server = AuthorizationServer(env)
    
    # Create resource server
    resource_server = ResourceServer(env, auth_server)
    
    # Register client application
    client_id = "photo_app"
    client_secret = "secret_xyz"
    redirect_uri = "https://photoapp.example.com/callback"
    
    auth_server.register_client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris=[redirect_uri]
    )
    
    # Create client
    client = OAuthClient(
        env,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        auth_server=auth_server,
        resource_server=resource_server
    )
    
    # Run simulation
    env.run(until=20)


if __name__ == "__main__":
    run_basic_oauth_flow()
```

This demonstrates the complete OAuth dance: authorization request, user consent, code exchange, and API access.

## Security Considerations

OAuth implementations must address several security concerns:

**State Parameter**: Prevents CSRF attacks by ensuring the authorization response matches the original request.

**Authorization Code Expiry**: Codes must be short-lived (typically 10 minutes) and single-use to prevent replay attacks.

**Client Authentication**: Confidential clients must authenticate with client_secret when exchanging codes for tokens.

**Redirect URI Validation**: Must exactly match the registered URI to prevent authorization code interception.

**Token Expiry**: Access tokens should expire, forcing clients to refresh or re-authorize.

**HTTPS Only**: All OAuth endpoints must use HTTPS to prevent token interception.

## Real-World OAuth Flows

OAuth 2.0 defines several flows for different scenarios:

**Authorization Code Flow** (our example): For server-side web apps that can securely store client_secret.

**PKCE Flow**: For mobile and single-page apps that can't securely store secrets. Uses code_challenge and code_verifier.

**Implicit Flow** (deprecated): Direct token issuance without code exchange. Replaced by Authorization Code + PKCE.

**Client Credentials Flow**: For machine-to-machine authentication without user involvement.

**Resource Owner Password Flow** (discouraged): Direct username/password exchange for tokens. Only for highly trusted clients.

## Refresh Tokens

Access tokens expire quickly (typically 1 hour). Refresh tokens allow clients to get new access tokens without user interaction:

```python
@dataclass
class RefreshToken:
    """Refresh token for obtaining new access tokens."""
    token: str
    client_id: str
    scope: List[str]
    expires_at: float
    
    def is_valid(self, now: float) -> bool:
        return now < self.expires_at
```

The authorization server can issue refresh tokens alongside access tokens. Clients use refresh tokens to get new access tokens when they expire, maintaining long-lived sessions without storing passwords.

## OpenID Connect

OpenID Connect (OIDC) builds on OAuth 2.0 to add identity:

- **ID Token**: JWT containing user identity claims (name, email, etc.)
- **UserInfo Endpoint**: API to retrieve additional user information
- **Standard Scopes**: openid, profile, email, address, phone

OIDC enables single sign-on (SSO) across multiple applications while OAuth provides API access. They work together: OAuth says "what you can do," OIDC says "who you are."

## Token Introspection and Revocation

Production OAuth systems need token management:

**Introspection**: Resource servers can check token validity with the authorization server:
```
POST /introspect
token=access_token_here
```

**Revocation**: Users can revoke tokens through settings:
```
POST /revoke
token=access_token_here
```

This enables security features like "sign out of all devices" and "revoke third-party app access."

## Conclusion

OAuth 2.0 solves delegated authorization through token-based access control. The key principles are:

1. **Separation of concerns**: Client, auth server, and resource server have distinct roles
2. **No password sharing**: Clients never see user credentials
3. **Limited scope**: Tokens grant specific permissions, not full account access
4. **Time-limited access**: Tokens expire, forcing periodic re-authorization
5. **Revocable**: Users can revoke access without changing passwords

OAuth has become the foundation for API security on the web. Combined with OpenID Connect, it enables both API access and identity federation. Understanding OAuth is essential for building modern applications—whether you're implementing social login, integrating third-party APIs, or designing your own API authorization.

Our simulation demonstrates the core OAuth mechanics: authorization requests, code exchange, token validation, and scope enforcement. Production systems add more complexity—PKCE for mobile apps, refresh tokens for long-lived sessions, JWT for distributed validation—but the fundamental pattern remains the same.
