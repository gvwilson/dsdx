from asimpy import Environment
from broker import MessageBroker
from publisher import Publisher
from subscriber import Subscriber


def run_simulation():
    """Run a simulation of the message queue system."""
    env = Environment()
    broker = MessageBroker(env, buffer_size=10)

    # Create publishers
    Publisher(env, broker, "OrderService", "orders", interval=2.0)
    Publisher(env, broker, "UserService", "user-activity", interval=1.5)

    # Create subscribers
    # Fast subscriber handling orders
    inventory = Subscriber(env, broker, "Inventory", ["orders"], processing_time=0.5)

    # Slow subscriber handling orders
    email = Subscriber(env, broker, "Email", ["orders"], processing_time=3.0)

    # Subscriber handling multiple topics
    analytics = Subscriber(
        env, broker, "Analytics", ["orders", "user-activity"], processing_time=1.0
    )

    # Run simulation
    env.run(until=20)

    # Print statistics
    print("\n=== Statistics ===")
    print(f"Messages published: {broker.messages_published}")
    print(f"Messages delivered: {broker.messages_delivered}")
    print(f"Inventory received: {inventory.messages_received}")
    print(f"Email received: {email.messages_received}")
    print(f"Analytics received: {analytics.messages_received}")


if __name__ == "__main__":
    run_simulation()
