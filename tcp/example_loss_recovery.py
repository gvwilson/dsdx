"""TCP demonstration under extreme packet loss conditions."""

from asimpy import Environment
from unreliable_network import UnreliableNetwork
from tcp_connection import TCPConnection
from tcp_applications import TCPClient, TCPServer


def run_high_loss_scenario() -> None:
    """Demonstrate TCP under high packet loss conditions."""
    env = Environment()

    print("=" * 60)
    print("High Loss TCP Scenario")
    print("=" * 60)
    print("Testing TCP robustness with extreme conditions:")
    print("  - 40% packet loss (!!)")
    print("  - 20% packet reordering")
    print("  - 10% packet duplication")
    print("  - Larger message requiring multiple segments")
    print("=" * 60 + "\n")

    # Extremely unreliable network
    network = UnreliableNetwork(
        env,
        loss_rate=0.40,  # 40% packet loss!
        reorder_rate=0.20,  # 20% reordering
        duplicate_rate=0.10,  # 10% duplication
        delay_range=(0.2, 0.6),
    )

    # TCP with aggressive retransmission
    server_conn = TCPConnection(
        env,
        "10.0.0.1",
        5000,
        network,
        window_size=3,
        timeout=1.0,  # Faster retransmit
    )

    client_conn = TCPConnection(
        env, "10.0.0.2", 6000, network, window_size=3, timeout=1.0
    )

    # Create applications
    TCPServer(env, server_conn)

    # Transfer larger message that will require multiple segments
    message = (
        "This is a much longer message that will be split into multiple "
        "TCP segments. Despite 40% packet loss - which is extremely high - "
        "TCP will successfully deliver every byte through retransmission. "
        "You'll see many timeouts and retransmissions, but eventually "
        "the complete message arrives in perfect order. "
    ) * 5  # Repeat 5 times

    TCPClient(env, client_conn, "10.0.0.1", 5000, message)

    # Run simulation (longer time for high loss)
    env.run(until=40)

    # Print statistics
    network.print_statistics()
    client_conn.print_statistics()
    server_conn.print_statistics()

    # Verify delivery
    print(f"\n{'=' * 60}")
    print("Verification:")
    print("=" * 60)
    expected_bytes = len(message.encode("utf-8"))
    if server_conn.bytes_received == expected_bytes:
        print(f"✓ SUCCESS: All {expected_bytes} bytes delivered correctly!")
    else:
        print(f"✗ INCOMPLETE: {server_conn.bytes_received}/{expected_bytes} bytes")


if __name__ == "__main__":
    run_high_loss_scenario()
