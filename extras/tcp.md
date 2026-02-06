# Building TCP on UDP

Implementation of reliable TCP-like communication on top of unreliable UDP packet delivery using asimpy simulation.

## Overview

This tutorial demonstrates how TCP achieves reliable, ordered delivery over unreliable networks through sequence numbers, acknowledgments, retransmission, and sliding windows. The implementation handles packet loss, reordering, and duplication—showing how reliability emerges from unreliable components.

## Files

### Core Components

- `tcp_types.py` - Data structures (Packet, SegmentBuffer, ReceiveBuffer, states)
- `unreliable_network.py` - Simulates UDP-like unreliable packet delivery
- `tcp_connection.py` - TCP connection with reliability mechanisms
- `tcp_applications.py` - Client and server applications using TCP

### Examples

- `example_basic_tcp.py` - Basic reliable transfer with moderate packet loss
- `example_loss_recovery.py` - Extreme packet loss scenario (40% loss)

### Documentation

- `tcp_chapter.md` - Complete tutorial chapter with explanations

## Key Concepts

### Three-Way Handshake

Connection establishment synchronizes sequence numbers:

1. Client → Server: SYN (seq=x)
2. Server → Client: SYN-ACK (seq=y, ack=x+1)
3. Client → Server: ACK (ack=y+1)

### Sequence Numbers

Each byte transmitted has a unique sequence number. Receivers use these to:
- Detect missing data
- Reorder out-of-sequence packets
- Identify duplicate packets

### Cumulative Acknowledgments

ACKs indicate "I've received everything up to sequence number X."

Example:
- Sent: segments with seq=1000, 1400, 1800
- Received: 1000, 1800 (1400 lost)
- ACK: 1400 (requesting missing segment)
- After receiving 1400: ACK 2200 (acknowledging all)

### Sliding Window

Sender can have multiple unacknowledged packets in flight:

```
Window size = 4 segments

Sent:     [1000] [1400] [1800] [2200] | waiting...
          ^                         ^
          oldest unack'd            newest

After ACK 1800:
Sent:     [1800] [2200] [2600] [3000] | can send more
          ^                         ^
```

This maintains throughput despite round-trip latency.

### Retransmission on Timeout

If ACK doesn't arrive within timeout (RTO), retransmit:

```
Time 0.0: Send segment seq=1000
Time 2.0: TIMEOUT - no ACK received
Time 2.0: Retransmit seq=1000
Time 2.3: Receive ACK 1400
```

## Running the Examples

### Basic TCP

```bash
python example_basic_tcp.py
```

Demonstrates:
- Three-way handshake
- Reliable data transfer
- Handling 15% packet loss
- Automatic retransmission
- In-order delivery

### High Loss Recovery

```bash
python example_loss_recovery.py
```

Demonstrates:
- TCP under extreme conditions (40% loss)
- Multiple retransmissions
- Complete message delivery despite high loss
- Robustness of TCP mechanisms

## Architecture

```
Client Application
    |
    v
TCP Connection (Client)
    | - Sequence numbering
    | - Send buffer
    | - Receive buffer
    | - Retransmission timers
    v
Unreliable Network
    | - Packet loss (15-40%)
    | - Packet reordering
    | - Packet duplication
    | - Variable delay
    v
TCP Connection (Server)
    | - ACK generation
    | - Out-of-order handling
    | - Data delivery
    v
Server Application
```

## Reliability Mechanisms

### Packet Loss

```
Sent:     [seq=1000]  [seq=1400]  [seq=1800]
                          LOST!
Received: [seq=1000]                [seq=1800]
Buffered: [seq=1800] (waiting for 1400)

Timeout → Retransmit seq=1400
Received: [seq=1400]
Deliver:  [1000-1400-1800] in order to application
```

### Packet Reordering

```
Sent:     [seq=1000]  [seq=1400]  [seq=1800]
Received: [seq=1000]  [seq=1800]  [seq=1400]  (reordered!)

Buffer handles out-of-order:
  Receive 1000 → deliver immediately
  Receive 1800 → hold in buffer
  Receive 1400 → deliver 1400+1800
```

### Packet Duplication

```
Sent:     [seq=1000]
Received: [seq=1000]  [seq=1000]  (duplicate!)

Sequence number check:
  First 1000  → accept (seq == expected)
  Second 1000 → ignore (seq < expected)
```

## Performance Characteristics

### Throughput

```
Max throughput ≈ (window_size × segment_size) / RTT

With window=4, segment=1400 bytes, RTT=0.5s:
  ≈ (4 × 1400) / 0.5 = 11,200 bytes/second
```

### Loss Recovery Time

```
Time to recover from loss ≈ RTO (retransmission timeout)

With RTO=1.5s, single loss adds ~1.5s to transfer time
With 15% loss rate, expect 15% of segments to be retransmitted
```

### Efficiency

```
Efficiency = successful_bytes / (successful_bytes + retransmitted_bytes)

With 15% loss and perfect retransmission:
  ≈ 100 / (100 + 15) = 87%
```

## Real-World Applications

### QUIC Protocol

Google's QUIC rebuilds TCP-like reliability over UDP:
- Faster connection establishment (1-RTT)
- Better loss recovery (no head-of-line blocking)
- Multiplexing multiple streams
- Used by Chrome, YouTube, Google services

### Reliable UDP in Gaming

Games use reliable UDP libraries (ENet, RakNet):
- TCP's head-of-line blocking problematic for real-time
- Custom reliability for critical data (position, events)
- Unreliable delivery for non-critical (effects, sounds)

### File Transfer Protocols

BitTorrent, rsync, and custom protocols:
- Need TCP-like reliability
- Want control over congestion, ordering, retransmission
- Build custom protocols over UDP

## Production Considerations

### Adaptive Timeout

Real TCP measures RTT and adapts timeout:

```python
smoothed_RTT = 0.875 × smoothed_RTT + 0.125 × measured_RTT
RTT_variance = 0.75 × RTT_variance + 0.25 × |measured_RTT - smoothed_RTT|
RTO = smoothed_RTT + 4 × RTT_variance
```

### Congestion Control

Slow start and congestion avoidance:

```python
# Slow start: exponential window growth
if cwnd < ssthresh:
    cwnd += 1  # per ACK

# Congestion avoidance: linear growth
else:
    cwnd += 1/cwnd  # per ACK

# On loss detection:
ssthresh = cwnd / 2
cwnd = 1
```

### Fast Retransmit

Detect loss without timeout:

```python
if duplicate_ACK_count == 3:
    retransmit_immediately()
    # Don't wait for timeout
```

### Selective Acknowledgment (SACK)

Acknowledge non-contiguous blocks:

```
Normal ACK: "received up to 1400"
SACK:      "received up to 1400, also 2200-2600, 3000-3400"
          → only retransmit 1400-2200, 2600-3000
```

## Further Reading

- [RFC 793 - Transmission Control Protocol](https://tools.ietf.org/html/rfc793)
- [RFC 2018 - TCP Selective Acknowledgment](https://tools.ietf.org/html/rfc2018)
- [RFC 5681 - TCP Congestion Control](https://tools.ietf.org/html/rfc5681)
- [QUIC: A UDP-Based Multiplexed and Secure Transport](https://www.chromium.org/quic/)
- [TCP/IP Illustrated, Volume 1](https://www.amazon.com/TCP-Illustrated-Vol-Addison-Wesley-Professional/dp/0201633469)
