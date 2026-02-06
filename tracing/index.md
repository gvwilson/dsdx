# Distributed Tracing

When a user reports that your application is slow, where do you start?
In a monolithic application, you'd profile a single process.
But in a microservices architecture where a single request touches dozens of services, each making multiple database queries and external API calls, understanding performance becomes exponentially harder.
Distributed tracing solves this by tracking requests as they flow through your system, showing exactly where time is spent.

Google pioneered distributed tracing with Dapper in 2010, processing trillions of traces per day to monitor their vast microservices infrastructure.
The insights from Dapper led to open-source systems like Zipkin (from Twitter) and Jaeger (from Uber).
Today, distributed tracing is essential for any organization running microservices—it's the only way to understand system-wide behavior, diagnose latency issues, and meet SLA requirements.

Distributed tracing works by assigning each request a unique trace ID and tracking it through every service it touches.
Each service operation creates a "span" representing work done, with timing information and metadata.
By collecting these spans and stitching them together, you can visualize the entire request path, identify bottlenecks, and understand dependencies between services.

This pattern appears everywhere modern software runs: Stripe uses distributed tracing to debug payment flows, Netflix tracks video playback requests across hundreds of services, and Uber monitors ride requests through their complex service mesh.
Understanding distributed tracing is essential for operating distributed systems at scale.

## Core Concepts

Distributed tracing has several key abstractions:

**Trace**: The complete journey of a request through the system.
Identified by a unique trace ID.

**Span**: Represents a single unit of work.
Has a span ID, parent span ID, start time, duration, and metadata.
Spans form a tree structure representing the call graph.

**Context Propagation**: Passing trace and span IDs between services so they can be correlated.

**Sampling**: Recording only a fraction of traces to manage overhead and storage costs.

**Tags and Logs**: Metadata attached to spans for debugging (e.g., HTTP status code, database query).

The relationships work like this:
- A trace contains many spans
- Spans have parent-child relationships forming a tree
- Root span has no parent
- Context propagates through service boundaries

## Data Structures

Let's define the core types for distributed tracing:

```python
from asimpy import Environment, Process, Queue
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import random
import time as stdlib_time


@dataclass
class TraceContext:
    """Context propagated between services."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    sampled: bool = True
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"TraceContext(trace={self.trace_id[:8]}..., span={self.span_id[:8]}...)"


@dataclass
class Span:
    """Represents a unit of work in a trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self, end_time: float) -> None:
        """Mark span as complete."""
        self.end_time = end_time
        self.duration = end_time - self.start_time
    
    def add_tag(self, key: str, value: Any) -> None:
        """Add metadata tag to span."""
        self.tags[key] = value
    
    def add_log(self, message: str, **fields: Any) -> None:
        """Add log entry to span."""
        self.logs.append({
            "message": message,
            "timestamp": stdlib_time.time(),
            **fields
        })
    
    def __str__(self) -> str:
        status = f"{self.duration:.3f}s" if self.duration else "active"
        return f"Span({self.operation_name}, {status})"


@dataclass
class Trace:
    """Complete trace containing all spans."""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def add_span(self, span: Span) -> None:
        """Add span to trace."""
        self.spans.append(span)
        
        if self.start_time is None or span.start_time < self.start_time:
            self.start_time = span.start_time
        
        if span.end_time:
            if self.end_time is None or span.end_time > self.end_time:
                self.end_time = span.end_time
    
    def get_duration(self) -> Optional[float]:
        """Get total trace duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def get_root_span(self) -> Optional[Span]:
        """Get root span (no parent)."""
        for span in self.spans:
            if span.parent_span_id is None:
                return span
        return None
    
    def __str__(self) -> str:
        duration = self.get_duration()
        status = f"{duration:.3f}s" if duration else "incomplete"
        return f"Trace({self.trace_id[:8]}..., {len(self.spans)} spans, {status})"


class SamplingStrategy(Enum):
    """Sampling strategies for trace collection."""
    ALWAYS = "always"
    NEVER = "never"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITED = "rate_limited"


@dataclass
class ServiceRequest:
    """Request between services with trace context."""
    request_id: str
    context: TraceContext
    payload: Dict[str, Any]
    response_queue: Queue
    
    def __str__(self) -> str:
        return f"Request({self.request_id})"


@dataclass
class ServiceResponse:
    """Response from service."""
    request_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    
    def __str__(self) -> str:
        status = "success" if self.success else f"error: {self.error}"
        return f"Response({self.request_id}, {status})"
```

These structures represent the distributed tracing data model.
TraceContext propagates between services, Span tracks individual operations, and Trace aggregates spans.

## Trace Collector

The collector receives spans from services and assembles them into complete traces:

```python
class TraceCollector(Process):
    """Collects and aggregates spans into traces."""
    
    def init(self) -> None:
        self.span_queue: Queue = Queue(self._env)
        
        # Active traces (trace_id -> Trace)
        self.traces: Dict[str, Trace] = {}
        
        # Completed traces
        self.completed_traces: List[Trace] = []
        
        # Statistics
        self.spans_received = 0
        self.traces_completed = 0
        
        # Sampling
        self.sample_rate = 1.0  # Sample 100% by default
        
        print(f"[{self.now:.1f}] TraceCollector started")
    
    async def run(self) -> None:
        """Main collector loop."""
        while True:
            span = await self.span_queue.get()
            await self.process_span(span)
    
    async def process_span(self, span: Span) -> None:
        """Process incoming span."""
        self.spans_received += 1
        
        # Get or create trace
        if span.trace_id not in self.traces:
            self.traces[span.trace_id] = Trace(trace_id=span.trace_id)
        
        trace = self.traces[span.trace_id]
        trace.add_span(span)
        
        # Check if trace is complete
        if self.is_trace_complete(trace):
            self.complete_trace(trace)
    
    def is_trace_complete(self, trace: Trace) -> bool:
        """Check if all spans in trace are finished."""
        if not trace.spans:
            return False
        
        # All spans must be finished
        return all(span.end_time is not None for span in trace.spans)
    
    def complete_trace(self, trace: Trace) -> None:
        """Mark trace as complete and move to storage."""
        self.completed_traces.append(trace)
        self.traces_completed += 1
        
        del self.traces[trace.trace_id]
        
        # Analyze trace
        duration = trace.get_duration()
        print(f"\n[{self.now:.1f}] Completed {trace}")
        print(f"  Total duration: {duration:.3f}s")
        print(f"  Spans: {len(trace.spans)}")
        
        # Show span tree
        self.print_span_tree(trace)
    
    def print_span_tree(self, trace: Trace) -> None:
        """Print span tree structure."""
        root = trace.get_root_span()
        if not root:
            return
        
        print("  Span tree:")
        self._print_span_recursive(trace, root, indent=2)
    
    def _print_span_recursive(self, trace: Trace, span: Span, 
                             indent: int) -> None:
        """Recursively print span and children."""
        prefix = " " * indent + "└─"
        duration_str = f"{span.duration:.3f}s" if span.duration else "?"
        print(f"{prefix} {span.operation_name} ({span.service_name}) - {duration_str}")
        
        # Find children
        children = [s for s in trace.spans if s.parent_span_id == span.span_id]
        for child in sorted(children, key=lambda s: s.start_time):
            self._print_span_recursive(trace, child, indent + 2)
    
    def get_slow_traces(self, threshold: float) -> List[Trace]:
        """Find traces slower than threshold."""
        slow = []
        for trace in self.completed_traces:
            duration = trace.get_duration()
            if duration and duration > threshold:
                slow.append(trace)
        return slow


def generate_id(prefix: str = "") -> str:
    """Generate unique ID for trace or span."""
    return f"{prefix}{random.randint(1000000, 9999999)}"
```

The collector aggregates spans into traces and can analyze them to find performance issues.

## Instrumented Service

Services create spans for their operations and propagate context:

```python
class InstrumentedService(Process):
    """Service with distributed tracing instrumentation."""
    
    def init(self, service_name: str, collector: TraceCollector,
             downstream_services: Optional[List['InstrumentedService']] = None) -> None:
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
            context=request.context
        )
        
        span.add_tag("service", self.service_name)
        span.add_tag("request_id", request.request_id)
        
        print(f"[{self.now:.1f}] {self.service_name}: Processing {request}")
        
        try:
            # Simulate processing
            await self.timeout(random.uniform(0.1, 0.5))
            
            # Call downstream services if any
            downstream_data = {}
            if self.downstream_services:
                downstream_data = await self.call_downstream_services(span)
            
            # Finish span
            self.finish_span(span, success=True)
            
            # Send response
            await request.response_queue.put(ServiceResponse(
                request_id=request.request_id,
                success=True,
                data=downstream_data
            ))
            
        except Exception as e:
            # Log error in span
            span.add_log("error", error=str(e))
            span.add_tag("error", True)
            
            self.finish_span(span, success=False)
            
            await request.response_queue.put(ServiceResponse(
                request_id=request.request_id,
                success=False,
                error=str(e)
            ))
    
    def start_span(self, operation_name: str, 
                   context: TraceContext) -> Span:
        """Start a new span."""
        span = Span(
            trace_id=context.trace_id,
            span_id=generate_id("span_"),
            parent_span_id=context.span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=self.now
        )
        
        self.spans_created += 1
        return span
    
    def finish_span(self, span: Span, success: bool = True) -> None:
        """Finish span and send to collector."""
        span.finish(self.now)
        span.add_tag("success", success)
        
        # Send to collector (async)
        self._env.process(self._send_span_to_collector(span))
    
    async def _send_span_to_collector(self, span: Span) -> None:
        """Send span to collector."""
        # Simulate network delay
        await self.timeout(0.01)
        await self.collector.span_queue.put(span)
    
    async def call_downstream_services(self, parent_span: Span) -> Dict[str, Any]:
        """Call downstream services with trace propagation."""
        results = {}
        
        for service in self.downstream_services:
            # Create child span for downstream call
            call_span = Span(
                trace_id=parent_span.trace_id,
                span_id=generate_id("span_"),
                parent_span_id=parent_span.span_id,
                operation_name=f"call_{service.service_name}",
                service_name=self.service_name,
                start_time=self.now
            )
            
            call_span.add_tag("downstream_service", service.service_name)
            
            # Create context for downstream service
            downstream_context = TraceContext(
                trace_id=parent_span.trace_id,
                span_id=call_span.span_id,
                parent_span_id=parent_span.span_id
            )
            
            # Make downstream call
            response_queue: Queue = Queue(self._env)
            downstream_request = ServiceRequest(
                request_id=generate_id("req_"),
                context=downstream_context,
                payload={},
                response_queue=response_queue
            )
            
            await service.request_queue.put(downstream_request)
            response = await response_queue.get()
            
            # Finish call span
            call_span.finish(self.now)
            call_span.add_tag("success", response.success)
            
            await self.collector.span_queue.put(call_span)
            
            results[service.service_name] = response.data
        
        return results
```

Services create spans, propagate context, and send spans to the collector.

## Frontend Service

The frontend initiates traces and calls backend services:

```python
class FrontendService(Process):
    """Frontend service that initiates traces."""
    
    def init(self, service_name: str, collector: TraceCollector,
             backend_services: List[InstrumentedService]) -> None:
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
            await self.initiate_request(f"user_req_{i+1}")
    
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
            start_time=self.now
        )
        
        root_span.add_tag("request_id", request_id)
        root_span.add_tag("root", True)
        
        print(f"\n[{self.now:.1f}] {self.service_name}: Starting trace {trace_id[:12]}...")
        
        # Create context
        context = TraceContext(
            trace_id=trace_id,
            span_id=root_span_id,
            sampled=True
        )
        
        # Call backend services
        await self.call_backend_services(context, root_span)
        
        # Finish root span
        root_span.finish(self.now)
        await self.collector.span_queue.put(root_span)
    
    async def call_backend_services(self, context: TraceContext, 
                                    parent_span: Span) -> None:
        """Call backend services."""
        # Simulate calling multiple backend services
        for service in self.backend_services:
            # Create context for backend
            backend_context = TraceContext(
                trace_id=context.trace_id,
                span_id=generate_id("span_"),
                parent_span_id=parent_span.span_id
            )
            
            response_queue: Queue = Queue(self._env)
            request = ServiceRequest(
                request_id=generate_id("req_"),
                context=backend_context,
                payload={},
                response_queue=response_queue
            )
            
            await service.request_queue.put(request)
            await response_queue.get()
```

The frontend creates root spans and initiates traces that flow through the system.

## Basic Tracing Example

Let's see distributed tracing in action:

```python
def run_distributed_tracing() -> None:
    """Demonstrate distributed tracing across services."""
    env = Environment()
    
    # Create trace collector
    collector = TraceCollector(env)
    
    # Create service topology
    # Frontend -> [API Gateway -> [Auth Service, Data Service -> Database]]
    
    database = InstrumentedService(env, "Database", collector)
    
    data_service = InstrumentedService(
        env, "DataService", collector, 
        downstream_services=[database]
    )
    
    auth_service = InstrumentedService(env, "AuthService", collector)
    
    api_gateway = InstrumentedService(
        env, "APIGateway", collector,
        downstream_services=[auth_service, data_service]
    )
    
    frontend = FrontendService(
        env, "Frontend", collector,
        backend_services=[api_gateway]
    )
    
    # Run simulation
    env.run(until=15)
    
    # Print summary
    print("\n" + "="*60)
    print("Tracing Summary:")
    print("="*60)
    print(f"Total traces completed: {collector.traces_completed}")
    print(f"Total spans received: {collector.spans_received}")
    print(f"\nService statistics:")
    
    for service in [api_gateway, auth_service, data_service, database]:
        print(f"  {service.service_name}: "
              f"requests={service.requests_handled}, "
              f"spans={service.spans_created}")
    
    # Find slow traces
    slow = collector.get_slow_traces(threshold=2.0)
    if slow:
        print(f"\nSlow traces (>{2.0}s): {len(slow)}")
        for trace in slow:
            print(f"  {trace}")


if __name__ == "__main__":
    run_distributed_tracing()
```

This demonstrates how traces flow through a multi-tier service architecture.

## Sampling Strategies

Not all traces need to be recorded.
Sampling reduces overhead:

```python
class Sampler:
    """Sampling strategy for traces."""
    
    def __init__(self, strategy: SamplingStrategy, 
                 sample_rate: float = 0.1) -> None:
        self.strategy = strategy
        self.sample_rate = sample_rate
        self.traces_sampled = 0
    
    def should_sample(self, trace_id: str) -> bool:
        """Decide if trace should be sampled."""
        if self.strategy == SamplingStrategy.ALWAYS:
            return True
        
        elif self.strategy == SamplingStrategy.NEVER:
            return False
        
        elif self.strategy == SamplingStrategy.PROBABILISTIC:
            # Sample probabilistically
            if random.random() < self.sample_rate:
                self.traces_sampled += 1
                return True
            return False
        
        elif self.strategy == SamplingStrategy.RATE_LIMITED:
            # Simple rate limiting (not time-based in simulation)
            self.traces_sampled += 1
            return self.traces_sampled % int(1/self.sample_rate) == 0
        
        return False
```

Sampling is essential for production systems—recording every trace is prohibitively expensive.

## Key Tracing Concepts

### Context Propagation

Trace and span IDs must propagate across service boundaries:

```
HTTP Request Headers:
  X-Trace-Id: abc123
  X-Span-Id: def456
  X-Parent-Span-Id: ghi789
```

### Span Relationships

Spans form a tree:
```
Root Span (frontend.request)
  ├─ API Gateway Span
  │   ├─ Auth Service Span
  │   └─ Data Service Span
  │       └─ Database Span
  └─ Cache Service Span
```

### Tags vs Logs

**Tags**: Indexed metadata for filtering/searching
- `http.status_code=200`
- `db.type=postgres`
- `error=true`

**Logs**: Timestamped events within span
- "cache miss"
- "retry attempt 2"
- "error: connection timeout"

## Real-World Applications

**E-commerce Checkout**:
- Frontend → API Gateway → Cart Service → Inventory Service → Payment Service
- Trace shows which service is slow
- Identifies payment gateway latency

**Video Streaming**:
- Player → CDN → Origin → Transcoding Service
- Traces reveal buffering causes
- Monitors encode time

**Banking Transactions**:
- Mobile App → API → Fraud Detection → Account Service → Ledger
- Tracks transaction end-to-end
- Ensures SLA compliance

## Conclusion

Distributed tracing provides observability for microservices.
The key principles are:

1.  **Trace ID propagation**: Unique ID follows request through system
1.  **Span creation**: Each operation creates a span with timing
1.  **Parent-child relationships**: Spans form a tree representing call graph
1.  **Sampling**: Record fraction of traces to manage overhead
1.  **Aggregation**: Collector assembles spans into complete traces

While production systems add async instrumentation, sampling strategies, and storage backends,
the core pattern remains: propagate context, create spans, and aggregate traces.
This enables understanding and optimizing distributed systems at scale.
