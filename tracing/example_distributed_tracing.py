"""Basic distributed tracing demonstration."""

from asimpy import Environment
from trace_collector import TraceCollector
from instrumented_service import InstrumentedService
from frontend_service import FrontendService


def run_distributed_tracing() -> None:
    """Demonstrate distributed tracing across services."""
    env = Environment()

    # Create trace collector
    collector = TraceCollector(env)

    # Create service topology
    # Frontend -> [API Gateway -> [Auth Service, Data Service -> Database]]

    database = InstrumentedService(env, "Database", collector)

    data_service = InstrumentedService(
        env, "DataService", collector, downstream_services=[database]
    )

    auth_service = InstrumentedService(env, "AuthService", collector)

    api_gateway = InstrumentedService(
        env, "APIGateway", collector, downstream_services=[auth_service, data_service]
    )

    FrontendService(env, "Frontend", collector, backend_services=[api_gateway])

    # Run simulation
    env.run(until=15)

    # Print summary
    print("\n" + "=" * 60)
    print("Tracing Summary:")
    print("=" * 60)
    print(f"Total traces completed: {collector.traces_completed}")
    print(f"Total spans received: {collector.spans_received}")
    print("\nService statistics:")

    for service in [api_gateway, auth_service, data_service, database]:
        print(
            f"  {service.service_name}: "
            f"requests={service.requests_handled}, "
            f"spans={service.spans_created}"
        )

    # Find slow traces
    slow = collector.get_slow_traces(threshold=2.0)
    if slow:
        print(f"\nSlow traces (>2.0s): {len(slow)}")
        for trace in slow:
            print(f"  {trace}")


if __name__ == "__main__":
    run_distributed_tracing()
