# Domain Name System (DNS)

Every time you visit a website, send an email, or connect to a service, your computer translates human-readable names like "www.example.com" into IP addresses like "192.0.2.1".
The Domain Name System (DNS) is the distributed database that makes this possible.

DNS is one of the internet's most critical infrastructure components.
Without it, you'd need to memorize IP addresses for every website.
Even more importantly, DNS enables service mobility—a website can change servers (and IP addresses) without users noticing, because the DNS mapping can be updated.

DNS handles over a trillion queries per day.
It's used for web browsing, email routing, service discovery, content delivery networks, and even security systems that block malicious domains.
Understanding DNS helps you debug connectivity issues, optimize performance, and appreciate how distributed systems achieve massive scale.

## How DNS Works

DNS is a hierarchical, distributed database.
Instead of one central server knowing all domain names (which would be impossible to scale), the work is distributed across millions of servers organized in a tree structure.

The hierarchy works like this:

1. **Root servers** (`.`) - 13 root server systems worldwide (actually many more physical servers using anycast)
2. **Top-level domain (TLD) servers** (`.com`, `.org`, `.net`, etc.)
3. **Authoritative name servers** (specific to each domain like `example.com`)
4. **Recursive resolvers** (your ISP's DNS server or public DNS like 8.8.8.8)

When you look up `www.example.com`, your computer asks a recursive resolver, which may:
1. Ask a root server "where's `.com`?"
2. Ask the `.com` server "where's `example.com`?"
3. Ask the `example.com` server "what's `www.example.com`?"
4. Return the answer to you

This process is called recursive resolution. The key insight is that no single server needs to know everything—each server knows its piece of the hierarchy and where to find the next level.

## Caching: The Secret to DNS Performance

DNS would be unbearably slow if every lookup required multiple round-trips through the hierarchy.
The solution is caching: resolvers remember answers for a period (TTL - Time To Live).

With caching:
- Popular domains (like google.com) are cached at every level
- Most queries are answered from cache in milliseconds
- Only cache misses require full recursive resolution
- Root servers handle surprisingly few queries despite being at the top of the hierarchy

Caching is why changing a DNS record doesn't take effect immediately—old values persist in caches until their TTL expires.

## Record Types

DNS stores different types of records:

- **A**: Maps domain to IPv4 address
- **AAAA**: Maps domain to IPv6 address  
- **CNAME**: Alias (canonical name) - points one domain to another
- **NS**: Name server - delegates a zone to an authoritative server
- **MX**: Mail exchange - specifies mail servers for a domain

Our implementation will focus on A and CNAME records, which handle most web traffic.

## Implementation

Let's build a DNS system with asimpy. We'll create authoritative servers, recursive resolvers with caching, and clients.

First, the message structures:

<div data-inc="dns_message.py" data-filter="inc=recordtype"></div>
<div data-inc="dns_message.py" data-filter="inc=dnsrecord"></div>
<div data-inc="dns_message.py" data-filter="inc=dnsquery"></div>
<div data-inc="dns_message.py" data-filter="inc=dnsresponse"></div>

These classes represent DNS queries and responses. The `DNSRecord` includes a TTL (time to live) for caching.

Now the authoritative DNS server:

<div data-inc="authoritative_server.py" data-filter="inc=authserver"></div>

An authoritative server is responsible for a specific zone (like `example.com`).
It stores the actual DNS records and answers queries authoritatively.
Notice how it handles CNAME records by following the alias to find the final A record.

The recursive resolver is more complex because it must cache and coordinate with authoritative servers:

<div data-inc="recursive_resolver.py" data-filter="inc=cacheentry"></div>
<div data-inc="recursive_resolver.py" data-filter="inc=recursive"></div>

The resolver checks its cache first (saving network round-trips), and only queries authoritative servers on cache misses.
Each cached entry has an expiration time based on the record's TTL.

Our simplified resolver directly contacts authoritative servers. Real DNS resolvers walk the hierarchy starting from root servers, but the principle is the same: cache aggressively, query only when necessary.

Finally, the DNS client:

<div data-inc="dns_client.py" data-filter="inc=dnsclient"></div>

Clients send queries to recursive resolvers and wait for responses. In real systems, clients also cache locally and can query multiple resolvers for redundancy.

## Running a Simulation

Let's see DNS resolution in action:

<div data-inc="simulate.py" data-filter="inc=testclient"></div>
<div data-inc="simulate.py" data-filter="inc=simulate"></div>

When you run this simulation, you'll see:
1. First lookup of `www.example.com` is a cache miss - queries authoritative server
2. Second lookup is a cache hit - answered immediately from cache
3. Different domains are cache misses until they're cached
4. The cache hit rate improves as the simulation runs

This demonstrates why DNS caching is so powerful: the first user to look up a domain pays the full resolution cost, but subsequent users (or repeated lookups) get instant responses.

## DNS Hierarchy and Load Distribution

Let's simulate a more realistic DNS hierarchy with multiple clients and resolvers:

<div data-inc="dns_hierarchy.py" data-filter="inc=loadclient"></div>
<div data-inc="dns_hierarchy.py" data-filter="inc=hierarchy"></div>

This simulation demonstrates several key DNS properties:

1. **Multiple resolvers**: Different ISPs run different resolvers, each with its own cache
2. **Load distribution**: Popular domains are cached at many resolvers, reducing load on authoritative servers
3. **Cache effectiveness**: Even with multiple clients making many queries, authoritative servers handle only a fraction because of caching

In the output, notice how the cache hit rate increases over time as more domains get cached. This is exactly what happens on the real internet—popular domains are almost always cached.

## Real-World Considerations

Our implementation simplifies several DNS complexities:

1. **Hierarchy walking**: Real resolvers start at root servers and work down the hierarchy. We skip directly to authoritative servers for clarity.

2. **Multiple answers**: DNS records can have multiple values (like multiple A records for load balancing). Real clients choose among them.

3. **Negative caching**: DNS caches "this domain doesn't exist" responses to avoid repeatedly querying for non-existent domains.

4. **Security**: DNS was designed without security. DNSSEC adds cryptographic signatures to prevent spoofing and cache poisoning.

5. **Anycast**: Root servers use anycast (many servers share one IP address) to distribute load and improve availability.

6. **TTL selection**: Choosing TTLs involves tradeoffs. Low TTLs mean changes propagate quickly but increase query load. High TTLs reduce load but slow down changes.

## Why DNS Matters

DNS enables many critical internet functions:

**Load balancing**: A domain can have multiple A records, distributing traffic across servers. DNS round-robin is a simple load balancing technique.

**Failover**: By updating DNS records, traffic can be redirected from failed servers to healthy ones.

**Content delivery**: CDNs use DNS to direct users to nearby servers. When you look up `cdn.example.com`, the authoritative server returns different IP addresses based on your location.

**Service discovery**: Modern microservice architectures use DNS for services to find each other. Kubernetes, for example, creates DNS records for every service.

**Security**: DNS-based blocklists prevent connections to known malicious domains. Your DNS resolver might block malware domains automatically.

## Common DNS Problems

Understanding DNS helps debug common issues:

**Propagation delays**: When you change DNS records, old values persist in caches until TTLs expire. This is why DNS changes "take 24-48 hours to propagate"—it's caches expiring.

**Split-horizon DNS**: Internal and external clients may see different answers for the same domain. Your office's internal DNS might return private IPs for corporate services.

**DNS hijacking**: Attackers sometimes compromise DNS to redirect traffic. This is why DNSSEC and DNS-over-HTTPS exist.

**Performance**: DNS lookups add latency to every connection. This is why browsers cache DNS results and why HTTP/2 connection reuse is valuable.

## Conclusion

DNS demonstrates how to build a scalable distributed system through hierarchy and caching.
No single server knows everything, yet any client can look up any domain by traversing the hierarchy.
Caching ensures that common queries are fast while reducing load on authoritative servers.

The four-level hierarchy (root, TLD, authoritative, resolver) with aggressive caching handles trillions of queries daily with remarkable efficiency.
Understanding DNS helps you reason about distributed databases, caching strategies, and hierarchical systems.

Our asimpy implementation captures DNS's essence: authoritative servers hold records, recursive resolvers cache and coordinate, and clients make queries.
Real DNS adds sophistication (security, redundancy, geographical distribution), but the core pattern remains: distribute data hierarchically, cache aggressively, and provide a simple query interface.

DNS is often invisible until it breaks, but it's fundamental to how the internet works. Every network request depends on it.
