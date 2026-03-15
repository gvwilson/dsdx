# Building TCP on UDP

When you open a website, stream a video, or send an email,
you're almost certainly using [Transmission Control Protocol](g:tcp) (TCP).
TCP provides reliable, ordered delivery of data over the internet,
handling packet loss, reordering, and congestion automatically.
But TCP itself runs on top of UDP,
which only provides best-effort, unordered packet delivery with no guarantees.

Building a simplified TCP on top of UDP
demonstrates the core mechanisms that make reliable communication possible over unreliable networks:

-   Sequence numbers:
    Each byte has a sequence number.
    Receivers use these to detect missing data and reorder packets.

-   Acknowledgments (ACKs):
    Receivers send ACKs indicating what data they've received.
    Senders use ACKs to know what to retransmit.

-   Retransmission:
    If an ACK doesn't arrive within a timeout, the sender retransmits the data.

-   Cumulative ACKs:
    ACKs indicate that the receiver has received everything up to a particular message,
    which simplifies acknowledgment logic.

-   Sliding windows:
    Sender can have multiple unacknowledged packets in flight
    to maintain throughput despite round-trip latency.

Our TCP-over-UDP implementation consists of:

1.  `tcp_types.py`: core data structures.
1.  `unreliable_network.py`: simulates packet loss, reordering, duplication.
1.  `tcp_connection.py`: TCP connection with reliability mechanisms.
1.  `tcp_applications.py`: client and server applications

Let's examine each component in turn.

## Data Structures {: #tcp-data}

We start by defining the six types of packets our protocol will use:

<div data-inc="tcp_types.py" data-filter="inc=packettypes"></div>

and the seven different states that a connection can be in:

<div data-inc="tcp_types.py" data-filter="inc=connectionstate"></div>

The `Packet` structure mirrors a real TCP/IP packet header with source and destination addressing,
sequence and acknowledgment numbers,
packet type,
and payload data:

<div data-inc="tcp_types.py" data-filter="inc=packet"></div>

## Unreliable Network Layer {: #tcp-network}

Before building TCP, we need to simulate UDP's unreliable delivery.
`UnreliableNetwork` tracks per-packet statistics
and maintains a registry mapping address:port pairs to their receive queues:

<div data-inc="unreliable_network.py" data-filter="inc=network_init"></div>

`send_packet` applies the configured loss and duplication rates
before calling `_deliver_packet`,
which adds a random delay and optionally increases it to simulate reordering:

<div data-inc="unreliable_network.py" data-filter="inc=network_send"></div>

This simulates the way packets in real networks can be lost, delayed, reordered, or duplicated.
The network maintains a registry of endpoints and routes packets accordingly.

## TCP Connection {: #tcp-connection}

The TCP connection implements reliability over the unreliable network:

<div data-inc="tcp_connection.py" data-filter="inc=tcpinit"></div>

The connection maintains send and receive buffers.
The send buffer holds unacknowledged segments for potential retransmission.
The receive buffer handles out-of-order delivery by holding segments until gaps are filled.

The `run` loop reads packets from the receive queue and dispatches each one through `handle_packet`,
which routes SYN, SYN-ACK, ACK, and DATA packets to the appropriate handler:

<div data-inc="tcp_connection.py" data-filter="inc=tcp_run"></div>

## Three-Way Handshake {: #tcp-handshake}

TCP connection establishment uses three packets to synchronize state:

<div data-inc="tcp_connection.py" data-filter="inc=tcpconnect"></div>

The handshake sequence is:

1.  Client → Server: SYN (seq=x)
1.  Server → Client: SYN-ACK (seq=y, ack=x+1)
1.  Client → Server: ACK (ack=y+1)

This synchronizes sequence numbers and establishes bidirectional communication.

The server side of the handshake is handled by `listen_and_accept`,
which waits for a SYN packet and then delegates the response to `handle_syn`:

<div data-inc="tcp_connection.py" data-filter="inc=server_accept"></div>

## Sliding Window Protocol {: #tcp-window}

The sliding window allows multiple packets in flight:

<div data-inc="tcp_connection.py" data-filter="inc=tcpsend"></div>

The sender can have `window_size` unacknowledged packets in flight.
This maintains throughput even with high latency:
new packets are being sent while waiting for ACKs from earlier packets.

## Retransmission on Timeout {: #tcp-retrans}

If an ACK doesn't arrive within the timeout period,
the segment is retransmitted.
We use a separate `Process` to simulate each retransmission timer:

<div data-inc="tcp_connection.py" data-filter="inc=retransmission"></div>

Each time we sent a segment, we create a `RetransmissionTimer`:

```python
# In TCPConnection.send():
await self.network.send_packet(segment)

# Add to send buffer
self.send_buffer.append(buffer_entry)

# Start retransmission timer
RetransmissionTimer(self._env, self, buffer_entry)
```

Each segment has its own timer `Process`.
If the segment hasn't been acknowledged (i.e., is still in the send buffer)
when the timer expires,
it is retransmitted and a new timer starts.

When a DATA packet arrives,
`handle_data` adds it to the receive buffer,
extracts any newly contiguous data to deliver to the application,
and sends a cumulative ACK:

<div data-inc="tcp_connection.py" data-filter="inc=handle_data"></div>

## Handling Out-of-Order Delivery {: #tcp-order}

The receive buffer handles segments arriving out of order:

<div data-inc="tcp_types.py" data-filter="inc=receivebuffer"></div>

Segments are held until all gaps are filled.
When a contiguous block of data is available,
it's delivered to the application in order.

## Cumulative Acknowledgments {: #tcp-ack}

TCP uses cumulative ACKs,
i.e.,
each ACK indicates all data up to a sequence number has been received:

<div data-inc="tcp_connection.py" data-filter="inc=handleack"></div>

A single ACK can acknowledge multiple segments.
This is simpler than selective acknowledgments and works well when most data arrives in order.

## Basic Example {: #tcp-basic}

Let's see TCP in action:

<div data-inc="ex_basic.py" data-filter="inc=basicexample"></div>
<div data-inc="ex_basic.txt"></div>

Despite 15% packet loss and reordering,
TCP successfully delivers the complete message in order.

## High Loss Scenario {: #tcp-highloss}

Let's test TCP under extreme conditions:

<div data-inc="ex_loss_recovery.py" data-filter="inc=highlossexample"></div>
<div data-inc="ex_loss_recovery.txt"></div>

Even with 40% loss, TCP delivers the complete message:
there are many retransmissions but eventual success.

## Key TCP Concepts

**Sequence Number Space**:
Each byte transmitted has a unique sequence number.
For a message "Hello":

- Byte 'H' might be seq=1000
- Byte 'e' is seq=1001
- Byte 'l' is seq=1002
- And so on...

When acknowledging, the receiver sends back seq=1005,
meaning, "I've received everything up to 1005."

**Window Size and Throughput**:
The window size determines maximum throughput.
With:

- Window size = 4 segments
- Segment size = 1000 bytes
- Round-trip time = 0.5 seconds

the maximum throughput is approximately (4 × 1000) / 0.5 = 8000 bytes/second.
Larger windows enable higher throughput but require more buffering.

**Adaptive Retransmission**:
Our implementation uses a fixed timeout.
Real TCP measures round-trip time and adapts the timeout:

```
RTO = smoothed_RTT + 4 × RTT_variance
```

This balances responsiveness (short timeout) with avoiding spurious retransmissions (long timeout).

**Fast Retransmit**:
An optimization not in our implementation
is that if the sender receives three duplicate ACKs for the same sequence number,
it immediately retransmits without waiting for timeout.
This recovers from loss faster.

## Real-World Considerations

Production TCP implementations include features we've omitted:

-   **Selective Acknowledgments (SACK)** acknowledge non-contiguous blocks of data,
    which allows efficient retransmission of only the missing segments.

-   **Congestion Control**:
    Adapt sending rate to network capacity using algorithms like:
    - **Slow Start**: Exponentially increase window until loss detected
    - **Congestion Avoidance**: Linearly increase window
    - **Fast Recovery**: Reduce window on loss, then recover

-   **Nagle's Algorithm** batches small writes to reduce overhead.

-   **Path MTU Discovery**
    determines maximum packet size without fragmentation by testing increasingly large packets.

-   **Timestamp Options**
    improve RTT estimation and detect wrapped sequence numbers on high-speed networks.

## Performance Analysis

Let's analyze our TCP implementation's efficiency:
With 15% loss and 4-segment window:

-   approximately 15% of packets need retransmission;
-   the window allows 4 segments in flight; and
-   the average delay per segment is approximately RTT + (loss_rate × timeout)

The throughput efficiency is therefore

```
efficiency = successful_transmission_rate / available_bandwidth
           ≈ (1 - loss_rate) / (1 + loss_rate × retransmissions)
```
