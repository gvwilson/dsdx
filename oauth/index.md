# OAuth

When you use your identity on one site to sign in on another,
you're using [OAuth][oauth].
This protocol has become the standard way for applications to access user data
without ever seeing the user's password.
Understanding it is essential for understanding [single sign-on](g:single-sign-on),
API access control,
and third-party integrations on the internet.

OAuth solves a fundamental problem:
how do you give a third-party application limited access to your account without sharing your credentials?
Before the protocol was developed,
users had to give their username and password to every app,
which created security nightmares.
OAuth introduced the concept of time-limited credentials called [tokens](g:oauth-token)
with specific scopes that can be revoked without changing your password.

## The OAuth Flow {: #oauth-flow}

OAuth involves four parties working together.
The resource owner is typically the user who owns the data being accessed.
The client application wants to access that data.
The authorization server authenticates the user and issues tokens.
The resource server hosts the protected resources and enforces access control.

FIXME: diagram

The authorization flow works like this:

1.  When the client requests authorization, the application redirects the user to the authorization server.
2.  The user authenticates (logs in) and grants permission.
3.  The server issues a one-time authorization code and sends it to the client.
4.  The client authenticates itself and exchanges that one-time code for an access token.
5.  The client then uses the token to access protected resources, e.g., to call protected APIs.

The key feature is that the client never sees the user's password,
and the token has limited scope and lifetime.

<div class="callout">

OAuth 2.0 defines several other flows for other scenarios,
including Proof Key for Code Exchange (PKCE) for mobile and single-page apps that can't securely store secrets
and Client Credentials Flow for machine-to-machine authentication without user involvement.

</div>

## Message Types {: #oauth-messages}

The most common OAuth flow is the Authorization Code flow
designed for server-side applications.
Before looking at the servers themselves,
we need to understand the data types they exchange.

The foundation is a helper function that generates random strings for codes and tokens:

<div data-inc="oauth_types.py" data-filter="inc=token_func"></div>

The six message dataclasses come in three request-response pairs,
one for each phase of the protocol.
`AuthorizationRequest` carries the client's identity, the desired [scope](g:oauth-scope),
and a `state` token for [cross-site request forgery](g:csrf) (CSRF) protection.
`TokenRequest` carries the one-time code along with the client's own credentials
so the authorization server can verify who it is talking to.
`ResourceRequest` carries the access token so the resource server can check
whether the caller is allowed to see the requested data:

<div data-inc="oauth_types.py" data-filter="inc=message_types"></div>

The servers also need two internal record-keeping types.
An `AuthorizationCode` tracks whether a code has already been used
(codes are one-time-only) and when it expires.
An `AccessToken` records which client owns it, what scopes it covers,
and when it expires.
Both have an `is_valid` method that encapsulates this check:

<div data-inc="oauth_types.py" data-filter="inc=internal_types"></div>

The authorization code is short-lived (typically 10 minutes),
while access tokens last longer (often 1 hour).

## Authorization Server {: #oauth-authserver}

The authorization server is the [trust anchor](g:trust-anchor) of OAuth:
it verifies the user's identity, obtains consent, and issues tokens.
Its `init` method creates two incoming queues and three dictionaries
for tracking registered clients, issued codes, and active tokens:

<div data-inc="authorization_server.py" data-filter="inc=init"></div>

Before any client can use the server, it must be registered with a client ID,
a shared secret, and a list of allowed redirect URIs.
The redirect URI check is an important security constraint:
it prevents an attacker from registering a lookalike app and
redirecting authorization codes to a server they control:

<div data-inc="authorization_server.py" data-filter="inc=register"></div>

The server's event loop uses asimpy's `FirstOf` to wait on both queues simultaneously.
Whichever queue receives a message first wins;
the other request is automatically cancelled:

<div data-inc="authorization_server.py" data-filter="inc=run"></div>

When an authorization request arrives,
`handle_authorization_request` delegates to two helpers and handles the user consent simulation in between:

<div data-inc="authorization_server.py" data-filter="inc=handle_auth"></div>

`_validate_auth_request` checks that the client is registered and that the redirect URI is one the client pre-registered.
Checking the redirect URI here is an important security constraint:
without it, an attacker could register a lookalike application and redirect authorization codes to a server they control:

<div data-inc="authorization_server.py" data-filter="inc=validate_auth"></div>

`_issue_authorization_code` generates the code, records it in `auth_codes` with its expiry and scope,
and sends it back through the response queue embedded in the request:

<div data-inc="authorization_server.py" data-filter="inc=issue_code"></div>

When the client then presents that code to exchange it for a token,
`handle_token_request` is similarly short because all the checking is delegated:

<div data-inc="authorization_server.py" data-filter="inc=handle_token"></div>

`_validate_token_request` works through a chain of checks:
the client must exist, the secret must match, the code must exist and still be valid,
and the client and redirect URI in the token request must exactly match those in the original authorization request.
Any mismatch sends an error response and returns `None` so the caller can exit early.
The method constructs the error response once at the top rather than repeating it at each branch:

<div data-inc="authorization_server.py" data-filter="inc=validate_token"></div>

`_issue_access_token` marks the code as `used` before doing anything else.
This is the line that makes authorization codes one-time-only:
re-using a code is one of the classic attack vectors against OAuth,
so the flag must be set before the token is issued, not after:

<div data-inc="authorization_server.py" data-filter="inc=issue_token"></div>

## Resource Server {: #oauth-resserver}

The resource server hosts the protected API.
Its `init` method takes a reference to the authorization server
so it can look up tokens, and it stores a dictionary of protected resources
where each entry specifies the required scope and the data to return:

<div data-inc="resource_server.py" data-filter="inc=init"></div>

Critically, the resource server doesn't need to know anything about users,
only about tokens and scopes.
Its event loop is simpler than the authorization server's
because it has only one incoming queue:

<div data-inc="resource_server.py" data-filter="inc=run"></div>

When a request arrives, `handle_resource_request` delegates to two helpers
and sends the successful response only if both pass:

<div data-inc="resource_server.py" data-filter="inc=handle_resource"></div>

`_validate_token` looks the token up in the authorization server's table and checks it hasn't expired.
Because the resource server shares a reference to the authorization server,
it can read `access_tokens` directly without a network call—a simplification that real deployments
replace with a token introspection endpoint or a shared cache:

<div data-inc="resource_server.py" data-filter="inc=validate_token"></div>

`_check_resource_access` confirms the path exists and then checks scope using set operations.
The token must cover all scopes the resource requires, but may cover more,
so a token issued with `["profile", "photos"]` scope passes a check for a resource
that requires only `["profile"]`:

<div data-inc="resource_server.py" data-filter="inc=check_access"></div>

## OAuth Client {: #oauth-client}

The OAuth client orchestrates the authorization flow.
Its `init` method stores the client credentials and references to both servers,
and initializes `access_token` to `None` since no token has been issued yet:

<div data-inc="oauth_client.py" data-filter="inc=init"></div>

The client's `run` method calls three helper methods in sequence,
aborting if any step fails.
It requests authorization for the `profile` and `photos` scopes,
exchanges the resulting code for an access token,
then uses that token to make three API calls,
including one for `messages` that it was not granted access to:

<div data-inc="oauth_client.py" data-filter="inc=run"></div>

`request_authorization` generates a `state` token before sending the request.
This state value is a random string that the client includes in the request
and the server echoes back in the response.
The client checks that the echoed state matches the one it sent,
which detects CSRF attacks where an attacker
tricks a user's browser into sending a forged callback:

<div data-inc="oauth_client.py" data-filter="inc=request_auth"></div>

`exchange_code_for_token` packages the code with the client credentials
and sends the bundle to the token endpoint.
The client must authenticate itself here—not just the user—because the token endpoint
needs to confirm that the party asking for the token is the same one
that originally registered with the server:

<div data-inc="oauth_client.py" data-filter="inc=exchange_code"></div>

`access_resource` wraps the stored token in a `ResourceRequest` and
waits for the response.
The client never stores the user's password at any point in this flow;
it only ever handles codes and tokens:

<div data-inc="oauth_client.py" data-filter="inc=access_resource"></div>

## Basic OAuth Simulation {: #oauth-sim}

Putting it all together, the simulation creates an authorization server and resource server,
registers a client application called `photo_app`,
and then runs the complete three-step flow:

<div data-inc="ex_basic_oauth.py" data-filter="inc=sim"></div>

The output shows the servers processing requests in sequence,
the user authentication pause,
the code exchange,
and finally the resource access attempts—including the denied request for `messages`,
which the client was never granted permission to read.

<div data-inc="ex_basic_oauth.txt"></div>

## Refresh Tokens {: #oauth-refresh}

Access tokens expire quickly (typically 1 hour).
Refresh tokens allow clients to get new access tokens without user interaction.
A `RefreshToken` has the same structure as an access token
but is stored separately and used only to request a replacement:

<div data-inc="oauth_types.py" data-filter="inc=refresh"></div>

The authorization server can issue refresh tokens alongside access tokens.
Clients use refresh tokens to get new access tokens when they expire,
maintaining long-lived sessions without storing passwords.

## In the Real World {: #oauth-real}

Real OAuth implementations must address several security concerns that our simulation ignores.
For example,
they must ensure that an authorization response matches the original request
to prevent CSRF attacks.
They also need token management,
so that a resource server can check token validity with an authorization server
or a user can revoke a token in order to do things like sign out of all devices.
