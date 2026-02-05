# OAuth 2.0 Authorization Framework

Implementation of OAuth 2.0 authorization code flow demonstrating delegated authorization
and API access control without password sharing.

## Overview

OAuth 2.0 enables applications to access user data without ever seeing the user's password.
Through token-based authorization, users grant limited access to their resources with
specific scopes that can be revoked at any time.

## Files

### Core Components

- `oauth_types.py` - Data structures (requests, responses, tokens, codes)
- `authorization_server.py` - Issues authorization codes and access tokens
- `resource_server.py` - Protects API endpoints with token validation
- `oauth_client.py` - Third-party application requesting access

### Examples

- `example_basic_oauth.py` - Complete authorization code flow demonstration

## Key Concepts

### The Four Parties

1. **Resource Owner** (user): Owns the protected data
2. **Client** (app): Wants to access the user's data
3. **Authorization Server**: Authenticates users and issues tokens
4. **Resource Server** (API): Hosts the protected resources

### Authorization Code Flow

The most secure OAuth flow for server-side applications:

1. Client redirects user to authorization server
2. User authenticates and grants permissions
3. Authorization server issues short-lived authorization code
4. Client exchanges code for access token (authenticating with client_secret)
5. Client uses access token to access protected APIs

### Security Features

**State Parameter**: Prevents CSRF attacks by verifying the response matches the request

**Authorization Code Expiry**: Codes expire in 10 minutes and are single-use only

**Client Authentication**: Confidential clients must prove their identity with client_secret

**Redirect URI Validation**: Must exactly match registered URI to prevent code interception

**Token Expiry**: Access tokens expire (typically 1 hour) to limit exposure

**Scope-Based Access**: Tokens grant specific permissions, not full account access

## Running the Example

### Basic Authorization Flow

```bash
python example_basic_oauth.py
```

Shows complete OAuth flow:
- Client requests authorization with scopes ["profile", "photos"]
- User authenticates and grants permissions
- Client exchanges code for access token
- Client accesses /api/profile and /api/photos successfully
- Client fails to access /api/messages (insufficient scope)

## Architecture

```
Client Application
        |
        | 1. Authorization Request
        v
Authorization Server
        |
        | 2. User Login & Consent
        |
        | 3. Authorization Code
        v
Client Application
        |
        | 4. Exchange Code for Token
        |    (with client_secret)
        v
Authorization Server
        |
        | 5. Access Token
        v
Client Application
        |
        | 6. API Request (with token)
        v
Resource Server
        |
        | 7. Protected Data
        v
Client Application
```

## Security Validations

The implementation demonstrates critical security checks:

### Authorization Server

- Client ID validation
- Redirect URI must match registered value
- Authorization code must be unused and not expired
- Code must belong to requesting client
- Client must authenticate with correct secret

### Resource Server

- Access token must be valid and not expired
- Token must have required scope for resource
- Token validation is stateless (checks with auth server state)

## Real-World OAuth Flows

### Authorization Code Flow (Implemented)

For server-side web apps that can securely store client_secret.

### PKCE Flow

For mobile and single-page apps that cannot securely store secrets.
Uses code_challenge and code_verifier instead of client_secret.

### Client Credentials Flow

For machine-to-machine authentication without user involvement.
Service accounts and API-to-API communication.

### Implicit Flow (Deprecated)

Direct token issuance without code exchange.
Replaced by Authorization Code + PKCE for security.

## Token Types

### Authorization Code

- Short-lived (10 minutes)
- Single-use only
- Exchanged for access token
- Prevents token interception

### Access Token

- Bearer token for API access
- Expires in 1 hour (configurable)
- Scoped to specific permissions
- Validated by resource server

### Refresh Token

- Long-lived token for obtaining new access tokens
- Allows persistent sessions without storing passwords
- Can be revoked independently

## Scopes

Scopes define what a token can access:

- `profile`: Access to user profile information
- `photos`: Access to user photos
- `messages`: Access to user messages
- `openid`: Identity information (OpenID Connect)

Tokens are granted only the scopes the user approves.

## OpenID Connect

OpenID Connect (OIDC) extends OAuth 2.0 with identity:

- **ID Token**: JWT containing user identity claims
- **UserInfo Endpoint**: Additional user information API
- **Standard Scopes**: openid, profile, email, address, phone

OIDC enables single sign-on (SSO) while OAuth provides API access.

## Production Considerations

Real OAuth implementations need:

### HTTPS Everywhere

All OAuth endpoints must use HTTPS to prevent token interception.

### Secure Token Storage

- Server-side: Store in secure database, encrypt at rest
- Client-side: Use httpOnly cookies or secure storage APIs
- Never store in localStorage (XSS vulnerable)

### PKCE for Public Clients

Mobile and single-page apps should use PKCE extension instead of client_secret.

### Token Rotation

Implement refresh tokens to rotate access tokens without user re-authentication.

### Revocation Endpoint

Allow users to revoke tokens through settings page.

### Rate Limiting

Prevent brute-force attacks on token endpoint.

### Audit Logging

Log all token issuance and usage for security monitoring.

## Real-World Systems

### Google OAuth 2.0

- Authorization endpoint: accounts.google.com/o/oauth2/v2/auth
- Token endpoint: oauth2.googleapis.com/token
- Scopes: gmail.readonly, drive.file, userinfo.profile

### GitHub OAuth

- Authorization endpoint: github.com/login/oauth/authorize
- Token endpoint: github.com/login/oauth/access_token
- Scopes: repo, user, gist, notifications

### Auth0

- Full OAuth 2.0 and OpenID Connect provider
- Customizable login pages
- Social identity provider integration
- Multi-factor authentication

## Common Vulnerabilities

### CSRF Attacks

**Attack**: Attacker tricks user into authorizing malicious app
**Defense**: Validate state parameter matches original request

### Authorization Code Interception

**Attack**: Attacker intercepts authorization code via insecure redirect
**Defense**: Validate redirect_uri exactly, use HTTPS only

### Token Leakage

**Attack**: Tokens exposed in logs, URLs, or browser storage
**Defense**: Use POST requests, httpOnly cookies, encrypt tokens

### Scope Creep

**Attack**: Client requests more permissions than needed
**Defense**: Request minimal scopes, explain to users what each scope does

## Further Reading

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [OAuth 2.0 Threat Model](https://tools.ietf.org/html/rfc6819)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 for Browser-Based Apps](https://tools.ietf.org/html/draft-ietf-oauth-browser-based-apps)
