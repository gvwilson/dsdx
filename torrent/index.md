# BitTorrent Protocol

When you download a large Linux distribution ISO, a game update, or a software package, you might be using BitTorrent without even knowing it. BitTorrent revolutionized file sharing by turning traditional client-server downloads upside down: instead of downloading from a single server, you download pieces from dozens of peers simultaneously. The more popular a file, the faster it downloads—a property called "swarming" that makes BitTorrent uniquely efficient for distributing large files.

BitTorrent emerged in 2001 as a solution to a fundamental problem: how do you distribute large files to millions of people without overwhelming your servers? Traditional HTTP downloads create a bottleneck—the server's upload bandwidth limits how many people can download simultaneously. BitTorrent solves this by having downloaders help each other: as soon as you download a piece, you can share it with others. This creates a distributed system where upload capacity scales with demand.

This pattern powers countless systems: Linux distributions use BitTorrent for ISO distribution, game companies use it for patches and updates, academic institutions share datasets, and content delivery networks use BitTorrent-inspired protocols for video streaming. Understanding BitTorrent reveals fundamental principles of peer-to-peer systems, incentive design, and distributed consensus.

## The BitTorrent Architecture

BitTorrent involves several components working together:

1. **Torrent file**: Metadata describing the file(s) to download, including piece hashes and tracker URL
2. **Tracker**: Coordinates peers by providing lists of other peers in the swarm
3. **Peers**: Clients downloading and uploading pieces simultaneously
4. **Seeders**: Peers who have the complete file and only upload
5. **Leechers**: Peers who are still downloading

The protocol works through these steps:

1. **Obtain torrent file**: Contains metadata and tracker URL
2. **Contact tracker**: Get list of peers in the swarm
3. **Connect to peers**: Establish TCP connections with multiple peers
4. **Exchange piece information**: Tell peers what you have, learn what they have
5. **Download pieces**: Request rarest pieces first to maximize availability
6. **Upload to others**: Share pieces you've downloaded to maintain good standing
7. **Verify integrity**: Check each piece against SHA-1 hash from torrent
8. **Become seeder**: Continue uploading after completing download

The key insight is **tit-for-tat**: peers upload to those who upload to them. This creates incentives for cooperation without central enforcement.

## Core Data Structures

Let's start with the fundamental types:

<div data-inc="bittorrent_types.py" data-filter="inc=torrenttypes"></div>

These structures represent the protocol's messages and state. The bitfield is particularly important—it compactly represents which pieces a peer has.

## Tracker Implementation

The tracker coordinates the swarm by maintaining a list of active peers:

<div data-inc="tracker.py" data-filter="inc=tracker"></div>

The tracker is stateless—it just maintains the current list of peers. In production, trackers often use UDP for efficiency and can handle millions of peers.

## Peer Implementation

The peer is the heart of BitTorrent—it downloads pieces, uploads to others, and manages connections:

```python
class BitTorrentPeer(Process):
    """BitTorrent peer (leecher or seeder)."""
    
    def init(self, peer_id: str, metadata: TorrentMetadata, 
             tracker: Tracker, initial_pieces: Optional[List[Piece]] = None) -> None:
        self.peer_id = peer_id
        self.metadata = metadata
        self.tracker = tracker
        
        # Piece storage
        self.pieces: Dict[int, Piece] = {}
        if initial_pieces:
            for piece in initial_pieces:
                self.pieces[piece.index] = piece
        
        # Track which pieces we have
        self.bitfield = [i in self.pieces for i in range(metadata.total_pieces)]
        
        # Connection management
        self.peers: Dict[str, PeerInfo] = {}  # Known peers
        self.peer_bitfields: Dict[str, List[bool]] = {}  # What each peer has
        self.peer_queues: Dict[str, Queue] = {}  # Message queues to peers
        
        # Download state
        self.interested_peers: Set[str] = set()  # Peers interested in us
        self.choked_by: Set[str] = set()  # Peers choking us
        self.pending_requests: Dict[int, str] = {}  # piece_index -> peer_id
        
        # Statistics
        self.downloaded_bytes = sum(len(p.data) for p in self.pieces.values())
        self.uploaded_bytes = 0
        
        # Upload/download tracking for tit-for-tat
        self.upload_to_peer: Dict[str, int] = {}  # bytes uploaded to each peer
        self.download_from_peer: Dict[str, int] = {}  # bytes downloaded from each peer
        
        print(f"[{self.now:.1f}] Peer {self.peer_id}: Started with "
              f"{len(self.pieces)}/{metadata.total_pieces} pieces")
    
    async def run(self) -> None:
        """Main peer loop."""
        # Contact tracker
        await self.announce_to_tracker("started")
        
        # Connect to peers
        await self.timeout(0.5)
        await self.connect_to_peers()
        
        # Main download loop
        while not self.is_complete():
            await self.download_pieces()
            await self.timeout(1.0)
        
        print(f"[{self.now:.1f}] Peer {self.peer_id}: Download complete!")
        
        # Announce completion
        await self.announce_to_tracker("completed")
        
        # Continue seeding for a while
        await self.timeout(5.0)
        await self.announce_to_tracker("stopped")
    
    def is_complete(self) -> bool:
        """Check if we have all pieces."""
        return len(self.pieces) == self.metadata.total_pieces
    
    async def announce_to_tracker(self, event: str) -> None:
        """Announce to tracker and get peer list."""
        response_queue: Queue = Queue(self._env)
        
        bytes_left = (self.metadata.total_pieces - len(self.pieces)) * self.metadata.piece_length
        
        request = TrackerRequest(
            info_hash=self.metadata.info_hash,
            peer_id=self.peer_id,
            port=6881,
            uploaded=self.uploaded_bytes,
            downloaded=self.downloaded_bytes,
            left=bytes_left,
            event=event,
            response_queue=response_queue
        )
        
        await self.tracker.request_queue.put(request)
        response = await response_queue.get()
        
        # Add new peers
        for peer_info in response.peers:
            if peer_info.peer_id not in self.peers:
                self.peers[peer_info.peer_id] = peer_info
    
    async def connect_to_peers(self) -> None:
        """Initiate connections with known peers."""
        for peer_id, peer_info in self.peers.items():
            if peer_id not in self.peer_queues:
                # Create message queue for this peer
                self.peer_queues[peer_id] = Queue(self._env)
                
                # Send bitfield
                await self.send_bitfield_to_peer(peer_id)
                
                # Express interest if they have something we need
                await self.evaluate_interest(peer_id)
    
    async def send_bitfield_to_peer(self, peer_id: str) -> None:
        """Send our bitfield to a peer."""
        # In real implementation, would send over network
        # For simulation, we'll just record it
        print(f"[{self.now:.1f}] Peer {self.peer_id}: Sent bitfield to {peer_id}")
    
    async def evaluate_interest(self, peer_id: str) -> None:
        """Determine if we're interested in a peer."""
        if peer_id not in self.peer_bitfields:
            return
        
        peer_bitfield = self.peer_bitfields[peer_id]
        
        # Check if peer has pieces we need
        for i, has_piece in enumerate(peer_bitfield):
            if has_piece and i not in self.pieces:
                # We're interested!
                await self.send_message(peer_id, PeerMessage("interested"))
                return
    
    async def send_message(self, peer_id: str, message: PeerMessage) -> None:
        """Send message to peer."""
        if peer_id in self.peer_queues:
            await self.peer_queues[peer_id].put(message)
    
    async def download_pieces(self) -> None:
        """Download pieces from peers."""
        # Find pieces we need
        needed_pieces = [i for i in range(self.metadata.total_pieces) 
                        if i not in self.pieces]
        
        if not needed_pieces:
            return
        
        # Rarest first: prioritize pieces that few peers have
        piece_rarity = self.calculate_piece_rarity()
        needed_pieces.sort(key=lambda idx: piece_rarity.get(idx, 999))
        
        # Request pieces from unchoked peers
        for piece_idx in needed_pieces[:5]:  # Limit concurrent requests
            if piece_idx in self.pending_requests:
                continue
            
            # Find peer who has this piece and isn't choking us
            peer_id = self.find_peer_with_piece(piece_idx)
            if peer_id:
                await self.request_piece(peer_id, piece_idx)
                break
    
    def calculate_piece_rarity(self) -> Dict[int, int]:
        """Calculate how many peers have each piece (for rarest-first)."""
        rarity: Dict[int, int] = {}
        
        for peer_bitfield in self.peer_bitfields.values():
            for idx, has_piece in enumerate(peer_bitfield):
                if has_piece:
                    rarity[idx] = rarity.get(idx, 0) + 1
        
        return rarity
    
    def find_peer_with_piece(self, piece_idx: int) -> Optional[str]:
        """Find a peer who has a piece and isn't choking us."""
        candidates = []
        
        for peer_id, bitfield in self.peer_bitfields.items():
            if (peer_id not in self.choked_by and 
                piece_idx < len(bitfield) and 
                bitfield[piece_idx]):
                candidates.append(peer_id)
        
        return random.choice(candidates) if candidates else None
    
    async def request_piece(self, peer_id: str, piece_idx: int) -> None:
        """Request a piece from a peer."""
        print(f"[{self.now:.1f}] Peer {self.peer_id}: Requesting piece {piece_idx} "
              f"from {peer_id}")
        
        self.pending_requests[piece_idx] = peer_id
        await self.send_message(peer_id, PeerMessage("request", piece_idx))
    
    async def receive_piece(self, peer_id: str, piece: Piece) -> None:
        """Receive and verify a piece."""
        if not piece.verify():
            print(f"[{self.now:.1f}] Peer {self.peer_id}: Piece {piece.index} "
                  f"failed verification!")
            # In real implementation, would re-request
            return
        
        # Store piece
        self.pieces[piece.index] = piece
        self.bitfield[piece.index] = True
        self.downloaded_bytes += len(piece.data)
        
        # Track download from this peer
        self.download_from_peer[peer_id] = self.download_from_peer.get(peer_id, 0) + len(piece.data)
        
        # Remove from pending
        if piece.index in self.pending_requests:
            del self.pending_requests[piece.index]
        
        print(f"[{self.now:.1f}] Peer {self.peer_id}: Received piece {piece.index} "
              f"({len(self.pieces)}/{self.metadata.total_pieces})")
        
        # Notify other peers we have this piece
        await self.broadcast_have(piece.index)
    
    async def broadcast_have(self, piece_idx: int) -> None:
        """Tell all peers we have a new piece."""
        for peer_id in self.peer_queues:
            await self.send_message(peer_id, PeerMessage("have", piece_idx))
    
    async def handle_peer_request(self, peer_id: str, piece_idx: int) -> None:
        """Handle request for a piece from another peer."""
        if piece_idx not in self.pieces:
            return
        
        # Implement tit-for-tat: only upload to peers who upload to us
        if not self.should_upload_to(peer_id):
            print(f"[{self.now:.1f}] Peer {self.peer_id}: Choking {peer_id}")
            return
        
        piece = self.pieces[piece_idx]
        
        # Send piece
        await self.send_message(peer_id, PeerMessage("piece", piece))
        
        self.uploaded_bytes += len(piece.data)
        self.upload_to_peer[peer_id] = self.upload_to_peer.get(peer_id, 0) + len(piece.data)
        
        print(f"[{self.now:.1f}] Peer {self.peer_id}: Uploaded piece {piece_idx} "
              f"to {peer_id}")
    
    def should_upload_to(self, peer_id: str) -> bool:
        """Tit-for-tat: upload to peers who upload to us."""
        # Optimistic unchoking: occasionally upload to new peers
        if random.random() < 0.1:
            return True
        
        # Upload to top uploaders to us
        downloaded_from_peer = self.download_from_peer.get(peer_id, 0)
        return downloaded_from_peer > 0
```

The peer implements several key BitTorrent features: rarest-first piece selection, tit-for-tat uploads, and piece verification.

## Simplified Peer for Simulation

For our simulation, let's create a simplified peer interaction model:

<div data-inc="simplified_peer.py" data-filter="inc=simplifiedpeer"></div>

This simplified version captures the essence of BitTorrent without all the protocol complexity.

## Basic Simulation

Let's see BitTorrent in action:

<div data-inc="example_basic_bittorrent.py" data-filter="inc=basicexample"></div>

This shows how pieces propagate through the swarm—early peers help later peers, distributing the upload burden.

## Key BitTorrent Concepts

### Rarest First

Peers prioritize downloading the rarest pieces in the swarm. This ensures piece diversity—if everyone downloads common pieces, rare pieces might disappear if the only seeder leaves.

### Tit-for-Tat

Peers upload to those who upload to them. This creates incentive for cooperation without central enforcement. Peers who don't upload ("leechers") get poor download speeds.

### Optimistic Unchoking

Periodically upload to a random peer who isn't uploading to you. This gives new peers a chance to join the ecosystem and discover faster peers.

### Choking Algorithm

Peers limit uploads to their top 4-5 uploaders. This maximizes efficiency by focusing bandwidth on productive connections rather than spreading it thin.

### End Game Mode

When almost complete, aggressively request remaining pieces from all peers. Cancel duplicate requests when pieces arrive. This prevents the last few pieces from taking disproportionately long.

## DHT (Distributed Hash Table)

Modern BitTorrent doesn't require trackers. DHT creates a distributed database where peers can find other peers without a central server:

- Uses Kademlia algorithm
- Each peer stores information about nearby peers in ID space
- Provides tracker-like functionality in decentralized manner
- Resilient to tracker failures or censorship

## Security and Privacy

BitTorrent has several security considerations:

**Protocol Encryption**: Obfuscates traffic to bypass ISP throttling

**PEX (Peer Exchange)**: Peers share peer lists directly, reducing tracker dependency

**Magnet Links**: Reference torrents by info hash without needing .torrent file

**Private Trackers**: Require authentication, track ratios, encourage seeding

**Copyright Concerns**: BitTorrent is neutral technology but can distribute copyrighted content

## Real-World Applications

Beyond file sharing, BitTorrent's principles appear in:

**Content Delivery**: Twitter uses BitTorrent-inspired Murder for deploying code to servers

**Software Distribution**: Linux distributions, game updates, software patches

**Live Streaming**: Peer-assisted streaming reduces server load

**Blockchain**: Bitcoin and Ethereum use gossip protocols inspired by P2P systems

**IPFS**: InterPlanetary File System uses BitTorrent-like chunking and distribution

## Conclusion

BitTorrent demonstrates how to build efficient distributed systems through clever incentive design. The key principles are:

1. **Decentralization**: No single point of failure or bottleneck
2. **Swarming**: More demand creates more supply
3. **Incentive alignment**: Tit-for-tat encourages cooperation
4. **Piece verification**: Cryptographic hashes ensure integrity
5. **Rarest first**: Maintains piece diversity in the swarm

These patterns extend beyond file sharing to distributed databases, content delivery networks, and peer-to-peer systems generally. Understanding BitTorrent provides insight into how to coordinate distributed resources without central control—a fundamental challenge in distributed systems.

Our simulation captures the essence of BitTorrent: pieces flowing through a swarm, rarest-first selection, and peers helping each other. While production BitTorrent adds complexity—TCP connection management, detailed choking algorithms, DHT—the core ideas we've demonstrated remain central to how BitTorrent achieves its remarkable efficiency.
