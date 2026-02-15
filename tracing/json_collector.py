"""Trace collector that outputs JSON in OpenTelemetry-inspired format."""

import json
from asimpy import Queue
from tracing_types import BaseCollector, Span, Trace


class JSONTraceCollector(BaseCollector):
    """Collects spans and outputs them as JSON."""

    def init(self) -> None:
        self.span_queue = Queue(self._env)
        self.active_traces: dict[str, Trace] = {}
        self.completed_traces: list[Trace] = []
        self.spans_received = 0
        self.traces_completed = 0

    async def run(self) -> None:
        """Main collector loop."""
        while True:
            span = await self.span_queue.get()
            self.process_span(span)

    def process_span(self, span: Span) -> None:
        """Process incoming span."""
        self.spans_received += 1

        if span.trace_id not in self.active_traces:
            self.active_traces[span.trace_id] = Trace(trace_id=span.trace_id)

        trace = self.active_traces[span.trace_id]
        trace.add_span(span)

        if self.is_trace_complete(trace):
            self.complete_trace(trace)

    def is_trace_complete(self, trace: Trace) -> bool:
        """Check if all spans in trace are finished."""
        if not trace.spans:
            return False
        return all(span.end_time is not None for span in trace.spans)

    def complete_trace(self, trace: Trace) -> None:
        """Mark trace as complete and output as JSON."""
        self.completed_traces.append(trace)
        self.traces_completed += 1
        del self.active_traces[trace.trace_id]
        self.output_trace_json(trace)

    def output_trace_json(self, trace: Trace) -> None:
        """Output trace in JSON format."""
        trace_json = self.trace_to_json(trace)
        print(json.dumps(trace_json, indent=2))

    def trace_to_json(self, trace: Trace) -> dict:
        """Convert trace to JSON structure."""
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": "tutorial-service"},
                            }
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {
                                "name": "distributed-tracing-tutorial",
                                "version": "1.0.0",
                            },
                            "spans": [self.span_to_json(span) for span in trace.spans],
                        }
                    ],
                }
            ]
        }

    def span_to_json(self, span: Span) -> dict:
        """Convert span to JSON structure."""
        # Convert times to nanoseconds (OpenTelemetry uses nanos)
        start_time_nanos = int(span.start_time * 1_000_000_000)
        end_time_nanos = int(span.end_time * 1_000_000_000) if span.end_time else 0

        attributes: list[dict] = [
            {"key": "service.name", "value": {"stringValue": span.service_name}}
        ]

        # Add tags as attributes
        for key, value in span.tags.items():
            attr: dict = {"key": key}
            if isinstance(value, bool):
                attr["value"] = {"boolValue": value}
            elif isinstance(value, int):
                attr["value"] = {"intValue": value}
            elif isinstance(value, float):
                attr["value"] = {"doubleValue": value}
            else:
                attr["value"] = {"stringValue": str(value)}
            attributes.append(attr)

        span_json: dict = {
            "traceId": span.trace_id,
            "spanId": span.span_id,
            "name": span.operation_name,
            "kind": 1,  # SPAN_KIND_INTERNAL
            "startTimeUnixNano": start_time_nanos,
            "endTimeUnixNano": end_time_nanos,
            "attributes": attributes,
            "status": {"code": 1},  # STATUS_CODE_OK
        }

        # Add parent span ID if present
        if span.parent_span_id:
            span_json["parentSpanId"] = span.parent_span_id

        # Add logs as events
        if span.logs:
            events: list[dict] = []
            for log in span.logs:
                event_attrs: list[dict] = []
                for key, value in log.items():
                    if key not in ("timestamp", "message"):
                        event_attrs.append(
                            {"key": key, "value": {"stringValue": str(value)}}
                        )
                events.append({
                    "timeUnixNano": int(log.get("timestamp", 0) * 1_000_000_000),
                    "name": log.get("message", "event"),
                    "attributes": event_attrs,
                })
            span_json["events"] = events

        return span_json
