from asimpy import Environment
from broker import MessageBroker
from publisher import Publisher
from subscriber import Subscriber


# mccole: simulate
def run_simulation():
    """Run a simulation of the message queue system."""
    env = Environment()
    broker = MessageBroker(env, buffer_size=10)

    # Publishers.
    Publisher(env, broker, "OrderService", "orders", interval=2.0)
    Publisher(env, broker, "UserService", "user-activity", interval=1.5)

    # Fast and slow subscribers.
    inventory = Subscriber(env, broker, "Inventory", ["orders"], processing_time=0.5)
    email = Subscriber(env, broker, "Email", ["orders"], processing_time=3.0)

    # Subscriber handling multiple topics.
    analytics = Subscriber(
        env, broker, "Analytics", ["orders", "user-activity"], processing_time=1.0
    )

    # Run simulation and report.
    env.run(until=20)
    print("\n=== Statistics ===")
    print(f"Messages published: {broker.messages_published}")
    print(f"Messages delivered: {broker.messages_delivered}")
    print(f"Inventory received: {inventory.messages_received}")
    print(f"Email received: {email.messages_received}")
    print(f"Analytics received: {analytics.messages_received}")
# mccole: /simulate


if __name__ == "__main__":
    run_simulation()
