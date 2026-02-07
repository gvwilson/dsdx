# Domain Name System (DNS) Tutorial

This tutorial demonstrates how DNS translates domain names to IP addresses using a hierarchical, distributed architecture.

## Files

- `dns_message.py` - DNS query/response structures and record types
- `authoritative_server.py` - Authoritative DNS server for a zone
- `recursive_resolver.py` - Recursive resolver with caching
- `dns_client.py` - DNS client for performing lookups
- `dns_hierarchy.py` - Full DNS hierarchy simulation
- `simulate.py` - Basic DNS resolution simulation
- `index.md` - Complete tutorial documentation

## Running the Examples

### Basic DNS Resolution
```bash
python simulate.py
```

This shows DNS queries being resolved and cached, demonstrating cache hits and misses.

### DNS Hierarchy with Load Testing
```bash
python dns_hierarchy.py
```

This simulates multiple resolvers, authoritative servers, and clients to show how caching reduces load on authoritative servers.

## Requirements

```bash
pip install asimpy
```

## Key Concepts

1. **Hierarchical resolution**: Root → TLD → Authoritative servers
2. **Caching**: Resolvers cache responses based on TTL to improve performance
3. **Record types**: A (IPv4), CNAME (alias), NS (nameserver), etc.
4. **Recursive vs authoritative**: Resolvers do the work, authoritative servers hold the data
5. **TTL (Time To Live)**: Controls how long records can be cached

## How It Works

When looking up `www.example.com`:

1. Client queries recursive resolver
2. Resolver checks cache (cache hit = fast response)
3. On cache miss, resolver queries authoritative server for example.com
4. Authoritative server returns A record with IP address
5. Resolver caches result and returns to client
6. Subsequent queries are served from cache until TTL expires

## DNS Record Types

- **A**: Maps domain to IPv4 address (e.g., www.example.com → 192.0.2.1)
- **AAAA**: Maps domain to IPv6 address
- **CNAME**: Alias pointing to another domain
- **NS**: Specifies authoritative nameserver for a zone
- **MX**: Mail server for a domain

## Real-World Applications

- **Web browsing**: Every URL lookup requires DNS
- **Email routing**: MX records direct mail to the right servers
- **Load balancing**: Multiple A records distribute traffic
- **Content delivery**: CDNs use DNS to direct users to nearby servers
- **Service discovery**: Microservices use DNS to find each other

## Performance Optimization

DNS caching is crucial for performance:
- First query to a domain: ~100-200ms (full recursive resolution)
- Cached query: <1ms (served from cache)
- Cache hit rates: Often >90% for popular resolvers
- Reduces load on authoritative servers by 10-100x
