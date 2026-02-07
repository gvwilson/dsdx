# Network Time Protocol (NTP)

Time synchronization is critical in distributed systems.
When multiple computers need to coordinate actions, order events, or maintain consistency, they must agree on what time it is.
Network Time Protocol (NTP) solves this by allowing computers to synchronize their clocks over a network with millisecond precision.

NTP powers everything from financial trading systems (where microseconds matter for transaction ordering) to distributed databases (which use timestamps for conflict resolution) to authentication systems (where time-based tokens expire).
Without NTP, a database might apply updates in the wrong order, a security token might be rejected as expired, or log files from different servers might be impossible to correlate.

## How NTP Works

The challenge of clock synchronization is that network communication takes time.
If a server sends you "the current time is 12:00:00", by the time you receive that message, it's no longer 12:00:00—it's some amount later depending on network delay.

NTP solves this with a clever algorithm that measures both the clock offset (how far off your clock is) and the network delay.
It uses four timestamps:

- **t1**: Client send time (when the client sends the request)
- **t2**: Server receive time (when the server receives the request)
- **t3**: Server transmit time (when the server sends the response)
- **t4**: Client receive time (when the client receives the response)

From these four timestamps, NTP calculates:

```
offset = ((t2 - t1) + (t3 - t4)) / 2
delay = (t4 - t1) - (t3 - t2)
```

The offset tells you how to adjust your clock. The delay tells you how reliable this measurement is (lower delay means more accurate).

## The Stratum Hierarchy

NTP organizes time servers into levels called strata:

- **Stratum 0**: Reference clocks (atomic clocks, GPS receivers)
- **Stratum 1**: Servers directly connected to stratum 0 (primary time servers)
- **Stratum 2**: Servers that sync with stratum 1
- **Stratum 3**: Servers that sync with stratum 2
- And so on...

This hierarchy prevents circular dependencies and allows the system to scale. End-user computers typically sync with stratum 2 or 3 servers.

## Implementation

Let's build an NTP simulation using asimpy. We'll create servers, clients, and demonstrate clock synchronization.

First, the NTP message structure:

<div data-inc="ntp_message.py" data-filter="inc=ntpmessage"></div>

The message holds the four timestamps and includes methods to calculate offset and delay using the NTP formulas.

Now the NTP server:

<div data-inc="ntp_server.py" data-filter="inc=ntpserver"></div>

The server receives requests, records timestamps t2 and t3, and sends responses back to clients.
In our simulation, the server's clock is accurate (it uses `self.now` which is the simulation's true time).
The `stratum` field indicates this server's level in the time hierarchy.

The NTP client is more complex because it must adjust its own clock:

<div data-inc="ntp_client.py" data-filter="inc=ntpclient"></div>

The client maintains a `clock_offset` representing how far its local clock differs from true time.
When it syncs, it calculates the offset using the NTP algorithm and adjusts its clock accordingly.

Notice `get_local_time()` returns the client's view of time, which may differ from simulation time until synchronization occurs.

## Running a Simulation

Let's see clock synchronization in action:

<div data-inc="simulate.py" data-filter="inc=simulate"></div>

When you run this, you'll see clients starting with different clock offsets (some fast, some slow) and gradually converging toward the true time as they sync with the server.

Each client's clock offset decreases with each sync cycle. After a few iterations, all clients are within milliseconds of true time.

## Stratum Hierarchy

In real NTP deployments, servers form a hierarchy. Let's simulate this:

<div data-inc="stratum_hierarchy.py" data-filter="inc=stratumserver"></div>

<div data-inc="stratum_hierarchy.py" data-filter="inc=stratumclient"></div>

A stratum N server needs to both sync with stratum N-1 (as a client) and serve stratum N+1 clients (as a server).
We implement this with two separate processes that share clock state via a dictionary.
The client process syncs with upstream and updates the shared clock offset.
The server process reads from the shared clock offset when responding to downstream requests.

This separation demonstrates an important pattern in asimpy: when you need concurrent behaviors, create separate Process classes that share state through Python objects (like our `clock_state` dictionary).

<div data-inc="stratum_hierarchy.py" data-filter="inc=hierarchy"></div>

In this simulation, stratum 1 servers sync with reference clocks (simulated as perfect time), stratum 2 servers sync with stratum 1, and end clients sync with stratum 2.

The key insight is that synchronization error accumulates as you go down the hierarchy, but it's still accurate enough for most purposes. A stratum 3 client might be accurate to within a few milliseconds, which is perfectly adequate for log timestamps or cache expiration.

## Real-World Considerations

Our simulation simplifies several aspects of real NTP:

1. **Network jitter**: Real networks have variable delay. NTP uses statistical filtering to handle this.

2. **Clock drift**: Computer clocks drift over time due to temperature and crystal imperfections. NTP compensates by adjusting the clock frequency, not just the offset.

3. **Multiple servers**: Clients typically query multiple servers and use the median to filter out bad sources.

4. **Security**: NTP can be spoofed. Modern deployments use NTS (Network Time Security) for authentication.

5. **Precision**: Real NTP achieves millisecond accuracy over the internet and microsecond accuracy on LANs.

## Why This Matters

Clock synchronization is often invisible until it breaks. Consider these scenarios:

- **Distributed databases**: Cassandra uses timestamps to resolve conflicting writes. If clocks are skewed, the wrong value might win.

- **Security**: Kerberos tickets are time-limited. If a client's clock is wrong by more than 5 minutes, authentication fails.

- **Compliance**: Financial regulations require accurate timestamps on all trades. Being off by even seconds can violate regulations.

- **Debugging**: When troubleshooting a distributed system failure, accurate timestamps in logs are essential for understanding the sequence of events.

NTP is one of the oldest internet protocols (dating from 1985) but remains fundamental to modern systems. Understanding how it works helps you reason about time in distributed systems and appreciate the complexity of seemingly simple operations like "what time is it?"

## Conclusion

NTP demonstrates how to solve a fundamental distributed systems problem: establishing a shared view of time despite network delays and imperfect clocks.

The four-timestamp algorithm elegantly separates network delay from clock offset, allowing precise synchronization over unreliable networks.
The stratum hierarchy provides scalability without sacrificing accuracy.

Our asimpy implementation captures the essence of NTP: clients sync periodically with servers, calculate offset and delay, and adjust their clocks.
Real implementations add sophistication (filtering, drift compensation, security), but the core algorithm remains the same.

Time synchronization is a prerequisite for many distributed system techniques—from distributed transactions to event ordering to cache consistency.
NTP makes it practical.
