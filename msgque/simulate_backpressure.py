from asimpy import Environment
from backpressure_broker import BackpressureBroker
from backpressure_publisher import BackpressurePublisher
from subscriber import Subscriber


# mccole: backpressure_simulation
def run_backpressure_simulation():
    """Demonstrate backpressure in action."""
    env = Environment()

    # Small queue size to trigger backpressure quickly.
    broker = BackpressureBroker(env, max_queue_size=5)

    # Fast publisher.
    fast_publisher = BackpressurePublisher(
        env, broker, "FastPublisher", "events", base_interval=0.5
    )

    # Slow subscriber creates backpressure.
    slow_subscriber = Subscriber(
        env, broker, "SlowSubscriber", ["events"], processing_time=2.0
    )

    # Run simulation.
    env.run(until=30)

    print("\n=== Backpressure Statistics ===")
    print(f"Messages published: {broker.messages_published}")
    print(f"Messages delivered: {broker.messages_delivered}")
    print(f"Messages dropped: {broker.messages_dropped}")
    print(f"Backpressure events: {fast_publisher.backpressure_events}")
    print(f"Final interval: {fast_publisher.current_interval:.1f}s")
    print(f"Messages received: {slow_subscriber.messages_received}")


# mccole: /backpressure_simulation


if __name__ == "__main__":
    run_backpressure_simulation()
