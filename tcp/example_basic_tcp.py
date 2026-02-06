"""Basic TCP communication demonstration."""

from asimpy import Environment
from unreliable_network import UnreliableNetwork
from tcp_connection import TCPConnection
from tcp_applications import TCPClient, TCPServer


def run_basic_tcp() -> None:
    """Demonstrate basic TCP communication over unreliable network."""
    env = Environment()

    print("=" * 60)
    print("Basic TCP Demonstration")
    print("=" * 60)
    print("Testing TCP reliability with:")
    print("  - 15% packet loss")
    print("  - 10% packet reordering")
    print("  - 5% packet duplication")
    print("=" * 60 + "\n")

    # Create unreliable network
    network = UnreliableNetwork(
        env,
        loss_rate=0.15,  # 15% packet loss
        reorder_rate=0.10,  # 10% reordering
        duplicate_rate=0.05,  # 5% duplication
    )

    # Create server connection
    server_conn = TCPConnection(
        env, "192.168.1.100", 8080, network, window_size=4, timeout=1.5
    )

    # Create client connection
    client_conn = TCPConnection(
        env, "192.168.1.101", 9000, network, window_size=4, timeout=1.5
    )

    # Create applications
    TCPServer(env, server_conn)

    message = (
        "Hello from TCP client! This message will be delivered reliably "
        "despite packet loss, reordering, and duplication. TCP ensures "
        "that every byte arrives in the correct order through sequence "
        "numbers, acknowledgments, and retransmission."
    )

    TCPClient(env, client_conn, "192.168.1.100", 8080, message)

    # Run simulation
    env.run(until=20)

    # Print statistics
    network.print_statistics()
    client_conn.print_statistics()
    server_conn.print_statistics()


if __name__ == "__main__":
    run_basic_tcp()
