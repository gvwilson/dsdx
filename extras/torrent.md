# BitTorrent Protocol

Implementation of BitTorrent peer-to-peer file sharing protocol demonstrating
distributed content delivery and swarm intelligence.

## Overview

BitTorrent revolutionized file distribution by enabling peers to download and upload
simultaneously. As more people download a file, the download speed increases rather
than decreases—a phenomenon called "swarming" that makes BitTorrent uniquely efficient.

## Files

### Core Components

- `bittorrent_types.py` - Data structures (Piece, TorrentMetadata, PeerInfo, messages)
- `tracker.py` - Coordinates peers by maintaining swarm lists
- `simplified_peer.py` - Peer that downloads and uploads pieces

### Examples

- `example_basic_bittorrent.py` - Basic BitTorrent swarm with seeder and leechers
- `example_swarm_growth.py` - Demonstrates swarm growth over time

## Key Concepts

### The Four Roles

1. **Tracker**: Central coordinator that maintains peer lists
2. **Seeder**: Peer with complete file, only uploads
3. **Leecher**: Peer downloading the file
4. **Swarm**: All peers participating in sharing a file

### How BitTorrent Works

1. **Get torrent file**: Contains metadata and tracker URL
2. **Contact tracker**: Receive list of peers in swarm
3. **Connect to peers**: Exchange piece availability information
4. **Download pieces**: Request rarest pieces first
5. **Upload to others**: Share pieces as soon as downloaded
6. **Verify pieces**: Check SHA-1 hash for each piece
7. **Become seeder**: Continue uploading after completion

### Rarest First

Peers prioritize downloading the rarest pieces in the swarm. This ensures:
- Piece diversity across the swarm
- No pieces become critically rare
- Swarm remains healthy even if seeders leave

### Tit-for-Tat

Peers upload to those who upload to them. This creates incentives for cooperation:
- Peers who contribute get better download speeds
- Freeloaders receive poor service
- No central enforcement needed

### Piece Verification

Every piece has a SHA-1 hash. After downloading:
- Compute hash of received data
- Compare with expected hash from torrent metadata
- Re-request if verification fails
- Ensures data integrity without trusting peers

## Running Examples

### Basic BitTorrent

```bash
python example_basic_bittorrent.py
```

Shows:
- 1 seeder with all 10 pieces
- 3 leechers starting with no pieces
- Pieces flowing through the swarm
- Rarest-first selection in action
- Upload/download statistics

### Swarm Growth

```bash
python example_swarm_growth.py
```

Demonstrates:
- New peers joining swarm over time
- Piece propagation as swarm grows
- Early leechers becoming sources for late joiners
- Load distribution across multiple peers

## Architecture

```
Tracker
    |
    +-- Maintains peer lists
    |   Responds to announces
    |
Peers in Swarm
    |
    +-- Seeder (100% complete)
    |       |
    |       +-- Uploads to all leechers
    |
    +-- Leecher 1 (downloading)
    |       |
    |       +-- Downloads from seeder
    |       +-- Uploads to other leechers
    |
    +-- Leecher 2 (downloading)
            |
            +-- Downloads from seeder & leecher 1
            +-- Uploads pieces as acquired
```

## Protocol Features

### Piece Selection

**Rarest First**: Download pieces that fewest peers have
- Maintains piece diversity
- Prevents piece extinction
- Ensures swarm health

**Random First**: Initial pieces chosen randomly
- Allows quick participation in swarm
- Gets interesting content faster

**End Game**: When almost complete, aggressively request remaining pieces
- Request same pieces from multiple peers
- Cancel duplicates when received
- Prevents slow final pieces

### Choking Algorithm

Peers limit concurrent uploads to ~4-5 best uploaders:
- **Choked**: Not receiving data from this peer
- **Unchoked**: Actively receiving data
- **Interested**: Want data from peer
- **Not Interested**: Have all peer's pieces

### Optimistic Unchoking

Periodically upload to random peer regardless of their contribution:
- Gives new peers chance to participate
- Discovers faster peers
- Prevents starvation
- Occurs every 30 seconds typically

## Tracker Protocol

### Announce Request

Peers periodically announce to tracker:

```
GET /announce?info_hash=...&peer_id=...&port=...&uploaded=...&downloaded=...&left=...&event=...
```

**Parameters:**
- `info_hash`: Torrent identifier
- `peer_id`: Peer identifier
- `port`: Peer's listening port
- `uploaded`: Bytes uploaded
- `downloaded`: Bytes downloaded  
- `left`: Bytes remaining
- `event`: started | completed | stopped

### Announce Response

Tracker returns:

```
{
  "interval": 1800,
  "peers": [
    {"peer_id": "...", "ip": "...", "port": ...},
    ...
  ]
}
```

## Security Considerations

### Hash Verification

- Every piece verified against SHA-1 hash
- Prevents malicious peers from sending bad data
- Detects transmission errors

### Privacy Concerns

- Tracker sees all peer IPs
- Anyone can join swarm and see participant IPs
- Solutions: VPN, private trackers, I2P

### DHT (Distributed Hash Table)

Modern BitTorrent uses DHT for tracker-less operation:
- Kademlia-based distributed database
- Peers find other peers without central tracker
- Resistant to censorship and tracker failures

## Real-World Systems

### Public Torrents

- Linux ISOs (Ubuntu, Fedora, Arch)
- Open source software distributions
- Public domain media
- Academic datasets

### Private Trackers

- Require account and authentication
- Track upload/download ratios
- Enforce minimum seeding requirements
- Better quality control

### Commercial Use

- Blizzard Entertainment: Game updates
- Facebook: Internal code deployment
- Amazon: AWS data distribution
- Twitter: Server deployment (Murder)

## Performance Optimizations

### Connection Limits

- Typical: 40-80 simultaneous peer connections
- Too few: Underutilizes bandwidth
- Too many: Overhead dominates

### Request Pipelining

- Request multiple pieces in advance
- Keeps pipe full
- Reduces round-trip latency

### Piece Size

- Typical: 256 KB - 2 MB
- Smaller: More overhead, better granularity
- Larger: Less overhead, coarser distribution

### Super Seeding

Seeder sends each piece to one peer initially:
- That peer must share it with others
- Maximizes seeder's impact
- Used when seeder bandwidth is limited

## Protocol Extensions

### Fast Extension (BEP 6)

- Allows some requests even when choked
- Speeds up connection establishment
- Reduces latency

### Extension Protocol (BEP 10)

- Negotiates additional features
- ut_metadata: Request metadata from peers
- ut_pex: Peer exchange

### Magnet Links

- No .torrent file needed
- Reference by info_hash alone
- Fetch metadata from swarm
- Example: `magnet:?xt=urn:btih:...`

### WebTorrent

- BitTorrent over WebRTC
- Works in web browsers
- Used for peer-to-peer streaming

## Comparison with Other Protocols

| Feature | BitTorrent | HTTP | FTP |
|---------|-----------|------|-----|
| Distribution | P2P | Client-Server | Client-Server |
| Scalability | Excellent | Poor | Poor |
| Reliability | High | Medium | Medium |
| Bandwidth Use | Distributed | Centralized | Centralized |
| File Integrity | Verified | Optional | Optional |

## Further Reading

- [BitTorrent Protocol Specification](http://www.bittorrent.org/beps/bep_0003.html)
- [BitTorrent Enhancement Proposals](http://www.bittorrent.org/beps/bep_0000.html)
- [Incentives Build Robustness in BitTorrent](http://bittorrent.org/bittorrentecon.pdf)
- [DHT Protocol](http://www.bittorrent.org/beps/bep_0005.html)
- [BitTorrent Performance](https://www.cs.cornell.edu/people/egs/papers/bittorrent.pdf)
