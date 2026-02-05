"""Demonstration of swarm growth and piece propagation."""

from asimpy import Environment, Process
from typing import List
from tracker import Tracker
from simplified_peer import SimplifiedPeer
from bittorrent_types import TorrentMetadata


class PeerJoiner(Process):
    """Process that adds peers to swarm over time."""

    def init(
        self,
        metadata: TorrentMetadata,
        tracker: Tracker,
        peers_list: List[SimplifiedPeer],
    ) -> None:
        self.metadata = metadata
        self.tracker = tracker
        self.peers_list = peers_list
        self.peer_counter = 1

    async def run(self) -> None:
        """Add new peers periodically."""
        for _ in range(5):
            await self.timeout(3.0)

            # Create new peer with no pieces
            new_peer = SimplifiedPeer(
                self._env,
                f"Peer{self.peer_counter}",
                self.metadata,
                self.tracker,
                self.peers_list,
                initial_pieces=[],
            )
            self.peers_list.append(new_peer)
            self.peer_counter += 1

            # Update all peer lists
            for peer in self.peers_list:
                peer.other_peers = [p for p in self.peers_list if p != peer]


def run_swarm_growth() -> None:
    """Demonstrate swarm growth over time."""
    env = Environment()

    # Create tracker
    tracker = Tracker(env)

    # Create torrent metadata
    metadata = TorrentMetadata(
        info_hash="xyz789",
        piece_length=512 * 1024,  # 512 KB pieces
        total_pieces=20,
        piece_hashes=["hash" + str(i) for i in range(20)],
        file_name="bigfile.bin",
        file_size=20 * 512 * 1024,
        tracker_url="http://tracker.example.com:8080/announce",
    )

    print(f"[{env.now:.1f}] Created {metadata}\n")

    # Create initial seeder
    peers: List[SimplifiedPeer] = []
    seeder = SimplifiedPeer(
        env, "Seeder", metadata, tracker, peers, initial_pieces=list(range(20))
    )
    peers.append(seeder)

    # Create process that adds peers over time
    PeerJoiner(env, metadata, tracker, peers)

    # Run simulation
    env.run(until=40)

    # Print statistics
    print(f"\n{'=' * 60}")
    print("Final Statistics:")
    print("=" * 60)
    for peer in peers:
        complete_pct = len(peer.have_pieces) / metadata.total_pieces * 100
        print(
            f"{peer.peer_id}: Complete={complete_pct:.0f}%, "
            f"Downloaded={peer.downloaded_pieces}, "
            f"Uploaded={peer.uploaded_pieces}"
        )


if __name__ == "__main__":
    run_swarm_growth()
