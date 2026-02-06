"""TCP client and server applications."""

from asimpy import Process, FirstOf, Timeout
from tcp_connection import TCPConnection


class TCPClient(Process):
    """Client application using TCP."""

    def init(
        self,
        connection: TCPConnection,
        remote_addr: str,
        remote_port: int,
        message: str,
    ) -> None:
        self.connection = connection
        self.remote_addr = remote_addr
        self.remote_port = remote_port
        self.message = message

    async def run(self) -> None:
        """Connect and send message."""
        # Connect
        success = await self.connection.connect(self.remote_addr, self.remote_port)

        if not success:
            print(f"[{self.now:.1f}] Client: Connection failed")
            return

        # Send message
        data = self.message.encode("utf-8")
        print(f"\n[{self.now:.1f}] Client: Sending message ({len(data)} bytes)")
        print(
            f"  Message: '{self.message[:50]}{'...' if len(self.message) > 50 else ''}'"
        )
        await self.connection.send(data)

        # Wait for transmission to complete
        await self.timeout(2.0)

        print(f"[{self.now:.1f}] Client: Done sending")


class TCPServer(Process):
    """Server application using TCP."""

    def init(self, connection: TCPConnection) -> None:
        self.connection = connection

    async def run(self) -> None:
        """Accept connection and receive data."""
        # Accept connection
        success = await self.connection.listen_and_accept()

        if not success:
            print(f"[{self.now:.1f}] Server: Accept failed")
            return

        print(f"\n[{self.now:.1f}] Server: Connection accepted, waiting for data")

        # Receive data
        received_data = b""
        timeout_time = self.now + 15.0

        while self.now < timeout_time:
            try:
                # Try to get data with timeout
                name, value = await FirstOf(
                    self._env,
                    data=self.connection.receive(),
                    timeout=Timeout(self._env, 0.5),
                )

                if name == "data":
                    chunk = value
                    received_data += chunk
                    print(
                        f"[{self.now:.1f}] Server: Received {len(chunk)} bytes "
                        f"(total: {len(received_data)})"
                    )
                    # Reset timeout
                    timeout_time = self.now + 15.0

            except Exception:
                # No data available
                await self.timeout(0.1)

        if received_data:
            message = received_data.decode("utf-8")
            print(f"\n[{self.now:.1f}] Server: Complete message received:")
            print(f"  Length: {len(message)} bytes")
            print(f"  Message: '{message[:100]}{'...' if len(message) > 100 else ''}'")
        else:
            print(f"\n[{self.now:.1f}] Server: No data received")

        print(f"[{self.now:.1f}] Server: Done")
