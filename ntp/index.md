# Network Time Protocol (NTP)

In order for computers to coordinate actions,
they must agree on what time it is.
[%g ntp "Network Time Protocol" %] (NTP) enables this
by giving computers a way to synchronize their clocks over a network with millisecond precision.
NTP dates from 1985,
but has survived largely unchanged because it works so well.

The challenge of clock synchronization is that network communication takes time.
If a server sends you "the current time is 12:00:00",
by the time you receive that message,
it's no longer 12:00:00,
and the amount of delay depends on the state of the network.
NTP solves this with an algorithm that measures both the clock offset
(how far off your clock is) and the network delay.
It uses four timestamps:

| label | name | purpose |
| ----- | ---- | ------- |
| t1    | the client send time | when the client sends the request |
| t2    | the server receive time | when the server receives the request |
| t3    | the server transmit time | when the server sends the response |
| t4    | the client receive time | when the client receives the response |

From these four timestamps, NTP calculates:

```
offset = ((t2 - t1) + (t3 - t4)) / 2
delay = (t4 - t1) - (t3 - t2)
```

The offset tells you how to adjust your clock,
while the delay tells you how reliable this measurement is
(lower delays are more accurate).

NTP organizes time servers into levels called [%g ntp-stratum "strata" %]:
Stratum 0 is reference clocks such as atomic clocks and GPS receivers.
Stratum 1 includes servers directly connected to stratum 0, which act as primary time servers.
Stratum 2 is servers that connect with stratum 1 servers, and so on.
This hierarchy prevents circular dependencies and allows the system to scale.
End-user computers typically sync with stratum 2 or 3 servers.

## Implementation {: #ntp-impl}

Our simulation starts with the NTP message structure:

[%inc ntp_message.py mark=ntpmessage %]

The message holds the four timestamps and includes methods to calculate offset and delay using the NTP formulas.

The NTP server receives requests, records timestamps t2 and t3, and sends responses back to clients.
In our simulation, the server's clock is accurate:
it uses `self.now`, which is the simulation's true time.
The `stratum` field indicates this server's level in the time hierarchy:

[%inc ntp_server.py mark=ntpserver %]

The NTP client is more complex because it must adjust its own clock.
The constructor stores the server queue,
sync interval,
simulated network delay,
and an initial clock offset that represents how far off the client starts:

[%inc ntp_client.py mark=client_init %]

The `run` method simply waits for each sync interval before calling `_sync_with_server`:

[%inc ntp_client.py mark=client_run %]

`_sync_with_server` executes one full NTP exchange.
It records the send time t1,
waits for the server's response containing t2 and t3,
records the receive time t4,
and then applies the calculated offset:

[%inc ntp_client.py mark=client_sync %]

The client maintains a `clock_offset` representing how far its local clock differs from true time.
When it syncs,
it calculates the offset using the NTP algorithm and adjusts its clock accordingly.
Notice that `get_local_time()` returns the client's view of time,
which may differ from simulation time until synchronization occurs.

## Running a Simulation

Let's see clock synchronization in action:

[%inc ex_usage.py mark=simulate %]

The output shows clients starting with different clock offsets—some fast, some slow—and
gradually converging toward the true time as they sync with the server.
After a few iterations, all clients are within milliseconds of true time.

[%inc ex_usage.out %]

## Stratum Hierarchy

In real NTP deployments, servers form a hierarchy.
Let's simulate this with a server:

[%inc ex_stratum.py mark=stratumserver %]

We also need a client for the stratum simulation:

[%inc ex_stratum.py mark=stratumclient %]

A stratum N server needs to both sync with stratum N-1 (as a client)
and serve stratum N+1 clients (as a server).
We implement this with two separate processes that share clock state via a dictionary.
The client process syncs with upstream and updates the shared clock offset.
The server process reads from the shared clock offset when responding to downstream requests.

[%inc ex_stratum.py mark=hierarchy %]

In this simulation,
stratum 1 servers sync with reference clocks (simulated as perfect time),
stratum 2 servers sync with stratum 1,
and end clients sync with stratum 2.
Synchronization error accumulates as you go down the hierarchy,
but it's still accurate enough for most purposes.
A stratum 3 client might be accurate to within a few milliseconds,
which is perfectly adequate for log timestamps or cache expiration.
