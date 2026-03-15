# Domain Name System (DNS)

Every time you visit a website or send an email,
your computer translates a human-readable name like "www.example.com"
into an IP addresses like "192.0.2.1".
[Domain Name System](g:dns) (DNS) is what makes this possible.
DNS is a distributed database,
and is one of the internet's most critical infrastructure components.
Among other things,
it enables service mobility:
a website can change servers and IP addresses without users noticing,
because the DNS mapping can be updated.

## How DNS Works

DNS is a hierarchical, distributed database that handles over a trillion queries per day.
Instead of one central server knowing all domain names,
which couldn't possibly scale,
the work is distributed across millions of servers organized in a tree structure:

-   13 [root servers](g:root-server)
    (though there are actually many more physical servers).
-   [Top-level domain](g:tld) (TLD) servers for `.com`, `.org`, `.net`, etc.
-   Authoritative name servers specific to each domain like `example.com`.
-   [Recursive resolvers](g:recursive-resolver),
    such as your ISP's DNS server or public DNS like 8.8.8.8.

When you look up `www.example.com`, your computer asks a recursive resolver, which may:

-   ask a root server "where's `.com`?"
-   ask the `.com` server "where's `example.com`?"
-   ask the `example.com` server "what's `www.example.com`?"
-   return the answer to you

This process is called recursive resolution.
It scales because no single server needs to know everything.
Instead,
each server knows its piece of the hierarchy and where to find the next level.

DNS would be unusably slow if every lookup required multiple round-trips through the hierarchy.
The solution is caching:
resolvers remember answers for a period referred to as [Time to Live](g:ttl) (TTL).
Popular domains like wikipedia.org are cached at every level
so that most queries are answered from cache in milliseconds.
This ensures that root servers handle surprisingly few queries
despite being at the top of the hierarchy.
It is also why changing a DNS record doesn't take effect immediately:
old values persist in caches until their TTL expires.

## Implementation {: #dns-impl}

DNS stores different types of records.
Our implementation will focus on A and CNAME records, which handle most web traffic.
As in previous chapters,
we start by enumerating the different types of records:

<div data-inc="dns_message.py" data-filter="inc=recordtype"></div>

and then define a DNS resource record:

<div data-inc="dns_message.py" data-filter="inc=dnsrecord"></div>

We also need to define the structure of queries and responses:

<div data-inc="dns_message.py" data-filter="inc=dnsquery"></div>
<div data-inc="dns_message.py" data-filter="inc=dnsresponse"></div>

The next step is to create the authoritative DNS server.
The constructor registers the zone this server is authoritative for and creates its record store.
`add_record` lets callers populate the zone before the simulation starts:

<div data-inc="authoritative_server.py" data-filter="inc=auth_init"></div>

The `run` loop receives queries and builds responses.
If the query domain ends in this server's zone,
the server looks up the record directly;
it also follows CNAME chains to resolve aliases to their target A records:

<div data-inc="authoritative_server.py" data-filter="inc=auth_run"></div>

The recursive resolver is more complex because it must cache and coordinate with authoritative servers.
A `CacheEntry` wraps a record with its expiry time:

<div data-inc="recursive_resolver.py" data-filter="inc=cacheentry"></div>

The resolver's constructor sets up the cache and tracks hit and miss statistics:

<div data-inc="recursive_resolver.py" data-filter="inc=resolver_init"></div>

The `run` loop checks the cache before forwarding to an authoritative server.
On a cache miss it calls `_resolve_recursive`, then stores the results:

<div data-inc="recursive_resolver.py" data-filter="inc=resolver_run"></div>

`_check_cache` filters out expired entries and returns `None` on a complete miss.
`_cache_records` stores records with expiry times computed from each record's TTL:

<div data-inc="recursive_resolver.py" data-filter="inc=resolver_cache"></div>

`_resolve_recursive` finds the authoritative server
whose zone suffix matches the query domain most specifically,
then forwards the query and returns the response.
Each cached entry has an expiration time based on the record's TTL.

<div data-inc="recursive_resolver.py" data-filter="inc=resolver_resolve"></div>

Our simplified resolver directly contacts authoritative servers.
Real DNS resolvers walk the hierarchy starting from root servers,
but the principle is the same:
cache aggressively, query only when necessary.

## Clients {: #dns-client}

The DNS client wraps a response queue and a query counter:

<div data-inc="dns_client.py" data-filter="inc=client_init"></div>

`lookup` constructs a query, sends it to the resolver, and prints the response:

<div data-inc="dns_client.py" data-filter="inc=client_lookup"></div>

Clients send queries to recursive resolvers and wait for responses.
In real systems,
clients also cache locally and can query multiple resolvers for redundancy.

## Running a Simulation

Let's see DNS resolution in action by building a client:

<div data-inc="ex_usage.py" data-filter="inc=testclient"></div>

We can now create the overall simulation:

<div data-inc="ex_usage.py" data-filter="inc=simulate"></div>

The output shows that the first lookup of `www.example.com` is a cache miss,
necessitating a query to the authoritative server,
but the second lookup is a cache hit.
Different domains are cache misses until they're cached,
and the cache hit rate improves as the simulation runs.
In other words,
the first user to look up a domain pays the full resolution cost,
but subsequent users (or repeated lookups) get instant responses.

<div data-inc="ex_usage.txt"></div>

`ex_hierarchy.py` is a more comples simulation
that demonstrate several key properties of DNS,
including the use of ultiple resolvers,
load distribution,
and the effectiveness of multiple caches.
Its output shows how the cache hit rate increases over time as more domains get cached.

## Real-World Considerations

Our implementation simplifies several DNS complexities:

-   Hierarchy walking:
    Real resolvers start at root servers and work down the hierarchy.
    We skip directly to authoritative servers for clarity.

-   Multiple answers:
    DNS records can have multiple values (like multiple A records for load balancing).
    Real clients choose among them.

-   [Negative caching](g:negative-cache):
    DNS caches "this domain doesn't exist" responses to avoid repeatedly querying for non-existent domains.

-   Anycast:
    Root servers use anycast (many servers sharing one IP address)
    to distribute load and improve availability.

-   TTL selection:
    Low TTLs mean changes propagate quickly but increase query load.
    High TTLs reduce load but slow down changes.

The most important omission in our implementation,
however,
is security.
DNS was designed without it;
[DNSSEC](g:dnssec) adds cryptographic signatures to prevent spoofing and cache poisoning.
