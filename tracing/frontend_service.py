"""Frontend service that initiates distributed traces."""

from asimpy import Process, Queue
from typing import List
from tracing_types import TraceContext, Span, ServiceRequest, generate_id
from trace_collector import TraceCollector
from instrumented_service import InstrumentedService


class FrontendService(Process):
    """Frontend service that initiates traces."""

    def init(
        self,
        service_name: str,
        collector: TraceCollector,
        backend_services: List[InstrumentedService],
    ) -> None:
        self.service_name = service_name
        self.collector = collector
        self.backend_services = backend_services

        # Statistics
        self.requests_initiated = 0

        print(f"[{self.now:.1f}] {self.service_name} started")

    async def run(self) -> None:
        """Generate user requests."""
        # Simulate user requests
        for i in range(3):
            await self.timeout(2.0)
            await self.initiate_request(f"user_req_{i + 1}")

    async def initiate_request(self, request_id: str) -> None:
        """Initiate request with new trace."""
        self.requests_initiated += 1

        # Create new trace
        trace_id = generate_id("trace_")
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

        print(
            f"\n[{self.now:.1f}] {self.service_name}: Starting trace {trace_id[:12]}..."
        )

        # Create context
        context = TraceContext(trace_id=trace_id, span_id=root_span_id, sampled=True)

        # Call backend services
        await self.call_backend_services(context, root_span)

        # Finish root span
        root_span.finish(self.now)
        await self.collector.span_queue.put(root_span)

    async def call_backend_services(
        self, context: TraceContext, parent_span: Span
    ) -> None:
        """Call backend services."""
        # Simulate calling multiple backend services
        for service in self.backend_services:
            # Create context for backend
            backend_context = TraceContext(
                trace_id=context.trace_id,
                span_id=generate_id("span_"),
                parent_span_id=parent_span.span_id,
            )

            response_queue: Queue = Queue(self._env)
            request = ServiceRequest(
                request_id=generate_id("req_"),
                context=backend_context,
                payload={},
                response_queue=response_queue,
            )

            await service.request_queue.put(request)
            await response_queue.get()
