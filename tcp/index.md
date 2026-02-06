# Building TCP on UDP

When you open a website, stream a video, or send an email,
you're almost certainly using TCP (Transmission Control Protocol).
TCP provides reliable, ordered delivery of data over the internet,
handling packet loss, reordering, and congestion automatically.
But TCP itself runs on top of UDP,
which only provides best-effort, unordered packet delivery with no guarantees.

Building a simplified TCP on top of UDP demonstrates
the core mechanisms that make reliable communication possible over unreliable networks:
sequence numbers for ordering,
acknowledgments for reliability,
retransmission timers for handling loss,
and flow control for preventing overwhelm.
These same principles appear throughout distributed systems:
message queues use acknowledgments,
databases use write-ahead logs with sequence numbers,
and streaming protocols use sliding windows.

This pattern is fundamental to understanding how networks work.
Google's QUIC protocol reimplements TCP-like reliability over UDP to enable faster connection establishment.
Reliable UDP libraries like ENet power multiplayer games.

| Feature | UDP | Our TCP |
|---------|-----|---------|
| Reliability | None | Guaranteed delivery |
| Ordering | None | In-order delivery |
| Overhead | Minimal | Header + ACKs + retransmissions |
| Latency | Low | Higher (due to ACKs and retransmits) |
| Throughput | High | Lower (due to window limits) |
| Use Cases | Live video, gaming, DNS | File transfer, web, email |

## The TCP Guarantee

TCP provides a reliable byte stream abstraction over unreliable packet delivery:

1.  **Reliable delivery**: All data arrives or an error is reported
1.  **Ordered delivery**: Data arrives in the order sent
1.  **Flow control**: Receiver controls sender rate to prevent overflow
1.  **Congestion control**: Sender adapts to network capacity

UDP, in contrast, provides none of these guarantees:
packets can be lost, duplicated, reordered, or corrupted.
Our implementation will add reliability and ordering on top of UDP's unreliable datagram service.

## Core Mechanisms

TCP uses several key mechanisms:

-   **Sequence Numbers**: Each byte has a sequence number.
    Receivers use these to detect missing data and reorder packets.

-   **Acknowledgments (ACKs)**: Receivers send ACKs indicating what data they've received.
    Senders use ACKs to know what to retransmit.

-   **Retransmission**: If an ACK doesn't arrive within a timeout, the sender retransmits the data.

-   **Sliding Window**: Sender can have multiple unacknowledged packets in flight
    to maintain throughput despite round-trip latency.

-   **Cumulative ACKs**: ACKs indicate, "I've received everything up to sequence number X,"
    simplifying acknowledgment logic.

## Implementation Overview

Our TCP-over-UDP implementation consists of:

1.  `tcp_types.py`: Core data structures (Packet, SegmentBuffer, ReceiveBuffer)
1.  `unreliable_network.py`: Simulates packet loss, reordering, duplication
1.  `tcp_connection.py`: TCP connection with reliability mechanisms
1.  `tcp_applications.py`: Client and server applications
1.  `example_basic_tcp.py`: Basic reliable transfer demonstration
1.  `example_loss_recovery.py`: High packet loss scenario

Let's examine each component.

## Data Structures

The core types represent TCP segments and connection state:

```python
class PacketType(Enum):
    """Types of TCP packets."""
    SYN = "SYN"          # Synchronize (connection establishment)
    SYN_ACK = "SYN_ACK"  # Synchronize-Acknowledge
    ACK = "ACK"          # Acknowledge
    DATA = "DATA"        # Data packet
    FIN = "FIN"          # Finish (connection teardown)


@dataclass
class Packet:
    """A network packet (simulating IP + TCP)."""
    src_addr: str
    dst_addr: str
    src_port: int
    dst_port: int
    seq_num: int
    ack_num: int
    packet_type: PacketType
    data: bytes = b""
    window_size: int = 65535
```

The `Packet` structure mirrors a real TCP/IP packet header with source and destination addressing,
sequence and acknowledgment numbers,
packet type,
and payload data.

## Unreliable Network Layer

Before building TCP, we need to simulate UDP's unreliable delivery:

```python
class UnreliableNetwork(Process):
    """Simulates unreliable packet delivery (like UDP)."""
    
    def init(self, loss_rate: float = 0.1, 
             reorder_rate: float = 0.05,
             duplicate_rate: float = 0.02,
             delay_range: tuple = (0.1, 0.5)) -> None:
        self.loss_rate = loss_rate
        self.reorder_rate = reorder_rate
        self.duplicate_rate = duplicate_rate
        self.delay_range = delay_range
        
        # Network endpoints (address:port -> queue)
        self.endpoints: Dict[str, Queue] = {}
        
    async def send_packet(self, packet: Packet) -> None:
        """Send packet with simulated unreliability."""
        # Simulate packet loss
        if random.random() < self.loss_rate:
            print(f"[{self.now:.1f}] Network: LOST {packet}")
            return
        
        # Simulate packet duplication
        if random.random() < self.duplicate_rate:
            await self._deliver_packet(packet)
        
        # Deliver the packet
        await self._deliver_packet(packet)
```

This simulates the way packets in real networks can be lost, delayed, reordered, or duplicated.
The network maintains a registry of endpoints and routes packets accordingly.

## TCP Connection

The TCP connection implements reliability over the unreliable network:

```python
class TCPConnection(Process):
    """TCP connection with reliability over unreliable network."""
    
    def init(self, local_addr: str, local_port: int,
             network: UnreliableNetwork,
             window_size: int = 4,
             timeout: float = 2.0) -> None:
        self.local_addr = local_addr
        self.local_port = local_port
        self.network = network
        self.window_size = window_size
        self.rto = timeout
        
        # Sequence numbers
        self.send_seq = random.randint(1000, 9999)
        self.recv_seq = 0
        
        # Send buffer for unacknowledged segments
        self.send_buffer: List[SegmentBuffer] = []
        
        # Receive buffer for out-of-order segments
        self.recv_buffer = ReceiveBuffer()
```

The connection maintains send and receive buffers.
The send buffer holds unacknowledged segments for potential retransmission.
The receive buffer handles out-of-order delivery by holding segments until gaps are filled.

## Three-Way Handshake

TCP connection establishment uses three packets to synchronize state:

```python
async def connect(self, remote_addr: str, remote_port: int) -> bool:
    """Initiate TCP connection (3-way handshake)."""
    # Send SYN
    self.state = ConnectionState.SYN_SENT
    syn = Packet(
        src_addr=self.local_addr,
        dst_addr=remote_addr,
        src_port=self.local_port,
        dst_port=remote_port,
        seq_num=self.send_seq,
        ack_num=0,
        packet_type=PacketType.SYN
    )
    
    await self.network.send_packet(syn)
    
    # Wait for SYN-ACK
    # ... (timing logic)
    
    # Send final ACK
    # Connection established
```

The handshake sequence is:

1.  Client → Server: SYN (seq=x)
1.  Server → Client: SYN-ACK (seq=y, ack=x+1)
1.  Client → Server: ACK (ack=y+1)

This synchronizes sequence numbers and establishes bidirectional communication.

## Sliding Window Protocol

The sliding window allows multiple packets in flight:

```python
async def send(self, data: bytes) -> None:
    """Send data reliably using TCP."""
    offset = 0
    while offset < len(data):
        chunk = data[offset:offset + self.mtu]
        
        # Wait if send window is full
        while len(self.send_buffer) >= self.window_size:
            await self.timeout(0.1)
        
        # Create and send segment
        segment = Packet(
            src_addr=self.local_addr,
            dst_addr=self.remote_addr,
            seq_num=self.next_seq_num,
            packet_type=PacketType.DATA,
            data=chunk
        )
        
        await self.network.send_packet(segment)
        
        # Add to send buffer
        self.send_buffer.append(SegmentBuffer(
            seq_num=self.next_seq_num,
            data=chunk,
            sent_time=self.now
        ))
        
        # Start retransmission timer
        RetransmissionTimer(self._env, self, buffer_entry)
        
        self.next_seq_num += len(chunk)
        offset += len(chunk)
```

The sender can have `window_size` unacknowledged packets in flight.
This maintains throughput even with high latency:
new packets are being sent while waiting for ACKs from earlier packets.

## Retransmission on Timeout

If an ACK doesn't arrive within the timeout period, the segment is retransmitted.
We use a separate `Process` for each retransmission timer:

```python
class RetransmissionTimer(Process):
    """Timer process for retransmitting unacknowledged segments."""
    
    def init(self, connection: 'TCPConnection', segment: SegmentBuffer) -> None:
        self.connection = connection
        self.segment = segment
    
    async def run(self) -> None:
        """Wait for timeout, then retransmit if not acknowledged."""
        await self.timeout(self.connection.rto)
        
        # Check if still in send buffer (not yet acknowledged)
        if self.segment in self.connection.send_buffer:
            print(f"[{self.now:.1f}] TCP: TIMEOUT - Retransmitting "
                  f"seq={self.segment.seq_num}")
            
            self.connection.packets_retransmitted += 1
            self.segment.retransmit_count += 1
            
            # Retransmit
            packet = Packet(
                src_addr=self.connection.local_addr,
                dst_addr=self.connection.remote_addr,
                seq_num=self.segment.seq_num,
                packet_type=PacketType.DATA,
                data=self.segment.data
            )
            
            await self.connection.network.send_packet(packet)
            
            # Restart timer
            RetransmissionTimer(self._env, self.connection, self.segment)
```

When sending a segment, we create a `RetransmissionTimer` `Process`:

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

## Handling Out-of-Order Delivery

The receive buffer handles segments arriving out of order:

```python
@dataclass
class ReceiveBuffer:
    """Buffer for out-of-order received segments."""
    segments: Dict[int, bytes] = field(default_factory=dict)
    next_expected_seq: int = 0
    
    def add_segment(self, seq_num: int, data: bytes) -> None:
        """Add a segment to the receive buffer."""
        if seq_num >= self.next_expected_seq:
            self.segments[seq_num] = data
    
    def get_continuous_data(self) -> bytes:
        """Extract continuous data starting from next_expected_seq."""
        result = b""
        current_seq = self.next_expected_seq
        
        while current_seq in self.segments:
            segment = self.segments.pop(current_seq)
            result += segment
            current_seq += len(segment)
        
        if result:
            self.next_expected_seq = current_seq
        
        return result
```

Segments are held until all gaps are filled.
When a contiguous block of data is available, it's delivered to the application in order.

## Cumulative Acknowledgments

TCP uses cumulative ACKs,
i.e.,
each ACK indicates all data up to a sequence number has been received:

```python
async def handle_ack(self, packet: Packet) -> None:
    """Handle ACK packet."""
    ack_num = packet.ack_num
    
    # Remove acknowledged segments from send buffer
    acknowledged = []
    for seg in self.send_buffer[:]:
        if seg.seq_num < ack_num:
            acknowledged.append(seg)
            self.send_buffer.remove(seg)
    
    if acknowledged:
        self.send_base = ack_num
```

A single ACK can acknowledge multiple segments.
This is simpler than selective acknowledgments and works well when most data arrives in order.

## Basic Example

Let's see TCP in action:

```python
def run_basic_tcp() -> None:
    """Demonstrate basic TCP communication."""
    env = Environment()
    
    # Create unreliable network
    network = UnreliableNetwork(
        env,
        loss_rate=0.15,      # 15% packet loss
        reorder_rate=0.10,   # 10% reordering
        duplicate_rate=0.05  # 5% duplication
    )
    
    # Create server connection
    server_conn = TCPConnection(
        env, "192.168.1.100", 8080, network
    )
    
    # Create client connection
    client_conn = TCPConnection(
        env, "192.168.1.101", 9000, network
    )
    
    # Create applications
    server = TCPServer(env, server_conn)
    client = TCPClient(
        env, client_conn, "192.168.1.100", 8080,
        "Hello from TCP! This will arrive reliably despite packet loss."
    )
    
    # Run simulation
    env.run(until=20)
```

Despite 15% packet loss and reordering,
TCP successfully delivers the complete message in order.

## High Loss Scenario

Let's test TCP under extreme conditions:

```python
def run_high_loss_scenario() -> None:
    """Demonstrate TCP under high packet loss."""
    env = Environment()
    
    # Extremely unreliable network
    network = UnreliableNetwork(
        env,
        loss_rate=0.40,      # 40% packet loss!
        reorder_rate=0.20,   # 20% reordering
        duplicate_rate=0.10  # 10% duplication
    )
    
    # TCP with aggressive retransmission
    server_conn = TCPConnection(
        env, "10.0.0.1", 5000, network,
        window_size=3,
        timeout=1.0  # Faster retransmit
    )
    
    client_conn = TCPConnection(
        env, "10.0.0.2", 6000, network,
        window_size=3,
        timeout=1.0
    )
    
    # Transfer larger message
    server = TCPServer(env, server_conn)
    client = TCPClient(
        env, client_conn, "10.0.0.1", 5000,
        "This is a much longer message that will be split into multiple "
        "segments. Despite 40% packet loss, TCP will successfully deliver "
        "every byte through retransmission. " * 5
    )
    
    env.run(until=40)
```

Even with 40% loss, TCP delivers the complete message.
You'll see many retransmissions but eventual success.

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

## Conclusion

Building TCP on UDP reveals how reliability emerges from unreliable components.
The key principles are:

1.  **Sequence numbers** enable detecting loss and reordering
1.  **Acknowledgments** confirm successful delivery
1.  **Retransmission timers** recover from packet loss
1.  **Sliding windows** maintain throughput despite latency
1.  **Cumulative ACKs** simplify acknowledgment logic

These patterns appear throughout distributed systems:

-   **Message queues** use similar acknowledgment schemes
-   **Database replication** uses sequence numbers for ordering
-   **Consensus protocols** use timeouts for failure detection
-   **QUIC** rebuilds TCP-like reliability over UDP for faster handshakes
