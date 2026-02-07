# Network Time Protocol (NTP) Tutorial

This tutorial demonstrates how NTP achieves clock synchronization across distributed systems.

## Files

- `ntp_message.py` - NTP message structure with offset/delay calculations
- `ntp_server.py` - NTP server implementation
- `ntp_client.py` - NTP client with clock adjustment
- `stratum_hierarchy.py` - Demonstrates the stratum hierarchy
- `simulate.py` - Basic NTP synchronization simulation
- `index.md` - Complete tutorial documentation

## Running the Examples

### Basic Synchronization
```bash
python simulate.py
```

This shows multiple clients with different clock offsets synchronizing with a single NTP server.

### Stratum Hierarchy
```bash
python stratum_hierarchy.py
```

This demonstrates how NTP scales through a hierarchy of servers, with stratum 1 servers syncing with reference clocks, stratum 2 syncing with stratum 1, and clients syncing with stratum 2.

## Requirements

```bash
pip install asimpy
```

## Key Concepts

1. **Four-timestamp algorithm**: Uses t1, t2, t3, t4 to calculate clock offset and network delay
2. **Clock adjustment**: Clients adjust their local clocks based on calculated offset
3. **Stratum hierarchy**: Prevents circular dependencies and enables scalability
4. **Periodic synchronization**: Clients sync at regular intervals to compensate for clock drift

## How It Works

NTP solves the challenge of network delay by using four timestamps:
- t1: Client send time
- t2: Server receive time  
- t3: Server transmit time
- t4: Client receive time

From these, NTP calculates:
```
offset = ((t2 - t1) + (t3 - t4)) / 2
delay = (t4 - t1) - (t3 - t2)
```

The offset tells the client how to adjust its clock. The delay indicates measurement reliability.

## Real-World Applications

- **Distributed databases**: Require synchronized timestamps for consistency
- **Security systems**: Time-limited authentication tokens depend on accurate clocks
- **Financial systems**: Trading platforms need precise timestamps for ordering
- **Logging and debugging**: Coordinating logs from multiple servers requires synchronized time
