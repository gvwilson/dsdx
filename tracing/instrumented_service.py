"""Instrumented service with distributed tracing."""

from asimpy import Process, Queue
from typing import List, Optional, Dict, Any
from tracing_types import (
    TraceContext,
    Span,
    ServiceRequest,
    ServiceResponse,
    generate_id,
)
from trace_collector import TraceCollector
import random


class InstrumentedService(Process):
    """Service with distributed tracing instrumentation."""

    def init(
        self,
        service_name: str,
        collector: TraceCollector,
        downstream_services: Optional[List["InstrumentedService"]] = None,
    ) -> None:
        self.service_name = service_name
        self.collector = collector
        self.downstream_services = downstream_services or []

        self.request_queue: Queue = Queue(self._env)

        # Statistics
        self.requests_handled = 0
        self.spans_created = 0

        print(f"[{self.now:.1f}] {self.service_name} started")

    async def run(self) -> None:
        """Handle incoming requests."""
        while True:
            request = await self.request_queue.get()
            await self.handle_request(request)

    async def handle_request(self, request: ServiceRequest) -> None:
        """Handle request with tracing."""
        self.requests_handled += 1

        # Create span for this operation
        span = self.start_span(
            operation_name=f"{self.service_name}.handle_request",
            context=request.context,
        )

        span.add_tag("service", self.service_name)
        span.add_tag("request_id", request.request_id)

        print(f"[{self.now:.1f}] {self.service_name}: Processing {request}")

        try:
            # Simulate processing
            await self.timeout(random.uniform(0.1, 0.5))

            # Call downstream services if any
            downstream_data: Dict[str, Any] = {}
            if self.downstream_services:
                downstream_data = await self.call_downstream_services(span)

            # Finish span
            self.finish_span(span, success=True)

            # Send response
            await request.response_queue.put(
                ServiceResponse(
                    request_id=request.request_id, success=True, data=downstream_data
                )
            )

        except Exception as e:
            # Log error in span
            span.add_log("error", error=str(e))
            span.add_tag("error", True)

            self.finish_span(span, success=False)

            await request.response_queue.put(
                ServiceResponse(
                    request_id=request.request_id, success=False, error=str(e)
                )
            )

    def start_span(self, operation_name: str, context: TraceContext) -> Span:
        """Start a new span."""
        span = Span(
            trace_id=context.trace_id,
            span_id=generate_id("span_"),
            parent_span_id=context.span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=self.now,
        )

        self.spans_created += 1
        return span

    def finish_span(self, span: Span, success: bool = True) -> None:
        """Finish span and send to collector."""
        span.finish(self.now)
        span.add_tag("success", success)

        # Send to collector (create a process wrapper)
        class SpanSender(Process):
            def init(self, target_span: Span, collector: TraceCollector) -> None:
                self.target_span = target_span
                self.collector = collector

            async def run(self) -> None:
                # Simulate network delay
                await self.timeout(0.01)
                await self.collector.span_queue.put(self.target_span)

        SpanSender(self._env, span, self.collector)

    async def call_downstream_services(self, parent_span: Span) -> Dict[str, Any]:
        """Call downstream services with trace propagation."""
        results: Dict[str, Any] = {}

        for service in self.downstream_services:
            # Create child span for downstream call
            call_span = Span(
                trace_id=parent_span.trace_id,
                span_id=generate_id("span_"),
                parent_span_id=parent_span.span_id,
                operation_name=f"call_{service.service_name}",
                service_name=self.service_name,
                start_time=self.now,
            )

            call_span.add_tag("downstream_service", service.service_name)

            # Create context for downstream service
            downstream_context = TraceContext(
                trace_id=parent_span.trace_id,
                span_id=call_span.span_id,
                parent_span_id=parent_span.span_id,
            )

            # Make downstream call
            response_queue: Queue = Queue(self._env)
            downstream_request = ServiceRequest(
                request_id=generate_id("req_"),
                context=downstream_context,
                payload={},
                response_queue=response_queue,
            )

            await service.request_queue.put(downstream_request)
            response = await response_queue.get()

            # Finish call span
            call_span.finish(self.now)
            call_span.add_tag("success", response.success)

            await self.collector.span_queue.put(call_span)

            results[service.service_name] = response.data

        return results
