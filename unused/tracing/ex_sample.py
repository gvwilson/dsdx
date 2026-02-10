"""Demonstrate sampling strategies for distributed tracing."""

from asimpy import Environment
from trace_collector import TraceCollector
from instrumented_service import InstrumentedService
from sampler import Sampler
from tracing_types import (
    SamplingStrategy,
    TraceContext,
    Span,
    ServiceRequest,
    generate_id,
)
from asimpy import Process, Queue


class SamplingFrontendService(Process):
    """Frontend service with sampling support."""

    def init(
        self,
        service_name: str,
        collector: TraceCollector,
        backend_services: list[InstrumentedService],
        sampler: Sampler,
    ) -> None:
        self.service_name = service_name
        self.collector = collector
        self.backend_services = backend_services
        self.sampler = sampler

        # Statistics
        self.requests_initiated = 0
        self.requests_sampled = 0
        self.requests_dropped = 0

        print(
            f"[{self.now:.1f}] {self.service_name} started with {sampler.strategy.value} sampling"
        )

    async def run(self) -> None:
        """Generate user requests."""
        # Generate more requests to show sampling effect
        for i in range(10):
            await self.timeout(0.5)
            await self.initiate_request(f"user_req_{i + 1}")

    async def initiate_request(self, request_id: str) -> None:
        """Initiate request with sampling decision."""
        self.requests_initiated += 1

        # Create trace ID
        trace_id = generate_id("trace_")

        # Make sampling decision
        should_sample = self.sampler.should_sample(trace_id)

        if not should_sample:
            self.requests_dropped += 1
            print(
                f"[{self.now:.1f}] {self.service_name}: Request {request_id} NOT SAMPLED"
            )
            # Still make the request, just don't trace it
            await self.make_untraced_request(request_id)
            return

        # Request is sampled - create trace
        self.requests_sampled += 1
        root_span_id = generate_id("span_")

        # Create root span
        root_span = Span(
            trace_id=trace_id,
            span_id=root_span_id,
            parent_span_id=None,
            operation_name="frontend.handle_user_request",
            service_name=self.service_name,
            start_time=self.now,
        )

        root_span.add_tag("request_id", request_id)
        root_span.add_tag("root", True)
        root_span.add_tag("sampled", True)

        print(
            f"[{self.now:.1f}] {self.service_name}: Request {request_id} SAMPLED (trace {trace_id[:12]}...)"
        )

        # Create context
        context = TraceContext(trace_id=trace_id, span_id=root_span_id, sampled=True)

        # Call backend services
        await self.call_backend_services(context, root_span)

        # Finish root span
        root_span.finish(self.now)
        self.collector.span_queue.put(root_span)

    async def make_untraced_request(self, request_id: str) -> None:
        """Make request without tracing."""
        for service in self.backend_services:
            # Create unsampled context
            context = TraceContext(
                trace_id=generate_id("trace_"),
                span_id=generate_id("span_"),
                sampled=False,  # Mark as unsampled
            )

            response_queue = Queue(self._env)
            request = ServiceRequest(
                request_id=generate_id("req_"),
                context=context,
                payload={},
                response_queue=response_queue,
            )

            service.request_queue.put(request)
            await response_queue.get()

    async def call_backend_services(
        self, context: TraceContext, parent_span: Span
    ) -> None:
        """Call backend services with tracing."""
        for service in self.backend_services:
            backend_context = TraceContext(
                trace_id=context.trace_id,
                span_id=generate_id("span_"),
                parent_span_id=parent_span.span_id,
            )

            response_queue = Queue(self._env)
            request = ServiceRequest(
                request_id=generate_id("req_"),
                context=backend_context,
                payload={},
                response_queue=response_queue,
            )

            service.request_queue.put(request)
            await response_queue.get()


def run_sampling_demo(strategy: SamplingStrategy, sample_rate: float = 0.3) -> None:
    """Run sampling demonstration."""
    print(f"\n{'=' * 60}")
    print(f"Testing {strategy.value} sampling (rate={sample_rate})")
    print("=" * 60)

    env = Environment()

    # Create trace collector
    collector = TraceCollector(env)

    # Create sampler
    sampler = Sampler(strategy, sample_rate=sample_rate)

    # Create simple service topology
    backend = InstrumentedService(env, "Backend", collector)

    frontend = SamplingFrontendService(
        env, "Frontend", collector, backend_services=[backend], sampler=sampler
    )

    # Run simulation
    env.run(until=6)

    # Print statistics
    print(f"\n{'=' * 60}")
    print("Sampling Statistics:")
    print("=" * 60)
    print(f"Requests initiated: {frontend.requests_initiated}")
    print(f"Requests sampled: {frontend.requests_sampled}")
    print(f"Requests dropped: {frontend.requests_dropped}")
    print(
        f"Sample rate: {frontend.requests_sampled / frontend.requests_initiated * 100:.1f}%"
    )
    print(f"Traces completed: {collector.traces_completed}")
    print(f"Spans received: {collector.spans_received}")


def run_all_sampling_strategies() -> None:
    """Demonstrate all sampling strategies."""

    # 1. Always sample (100%)
    run_sampling_demo(SamplingStrategy.ALWAYS, sample_rate=1.0)

    # 2. Never sample (0%)
    run_sampling_demo(SamplingStrategy.NEVER, sample_rate=0.0)

    # 3. Probabilistic (30%)
    run_sampling_demo(SamplingStrategy.PROBABILISTIC, sample_rate=0.3)

    # 4. Rate limited (every 3rd request)
    run_sampling_demo(SamplingStrategy.RATE_LIMITED, sample_rate=0.33)


if __name__ == "__main__":
    run_all_sampling_strategies()
