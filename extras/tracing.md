# Distributed Tracing

Implementation of distributed tracing for tracking requests across microservices,
inspired by Google's Dapper, Zipkin, and Jaeger.

## Overview

Distributed tracing tracks requests as they flow through multiple services, showing
exactly where time is spent. Each request gets a unique trace ID, and every service
operation creates a "span" with timing information. By collecting and aggregating spans,
you can visualize the complete request path and identify performance bottlenecks.

## Files

### Core Components

- `tracing_types.py` - Data structures (TraceContext, Span, Trace, requests/responses)
- `trace_collector.py` - Aggregates spans into complete traces
- `instrumented_service.py` - Service with tracing instrumentation
- `frontend_service.py` - Initiates traces for user requests

### Examples

- `example_distributed_tracing.py` - Multi-tier service architecture with tracing

## Key Concepts

### Core Abstractions

**Trace**: The complete journey of a request through the system
- Identified by unique trace ID
- Contains multiple spans
- Represents end-to-end request flow

**Span**: A unit of work within a trace
- Has span ID and parent span ID
- Tracks start time and duration
- Contains tags (metadata) and logs (events)
- Forms tree structure

**Context Propagation**: Passing trace/span IDs between services
- Trace ID stays constant
- Each service creates new span ID
- Parent span ID links spans together

**Sampling**: Recording fraction of traces to manage overhead
- Probabilistic: Random sampling
- Rate-limited: Fixed number per interval
- Always/Never: For testing

### Span Relationships

Spans form a parent-child tree:

```
Root Span (frontend.request)
  ├─ API Gateway Span
  │   ├─ Auth Service Span
  │   └─ Data Service Span
  │       └─ Database Span
  └─ Cache Service Span
```

### Tags vs Logs

**Tags**: Indexed metadata for searching
```python
span.add_tag("http.status_code", 200)
span.add_tag("db.type", "postgres")
span.add_tag("error", True)
```

**Logs**: Timestamped events within span
```python
span.add_log("cache miss")
span.add_log("retry attempt 2")
span.add_log("error: timeout")
```

## Running the Example

### Basic Distributed Tracing

```bash
python example_distributed_tracing.py
```

Shows:
- 3 user requests flowing through services
- Complete traces with timing information
- Span tree visualization
- Service statistics

## Architecture

```
Frontend (Root Span)
    |
    +-- Call API Gateway
            |
            +-- API Gateway Span
                    |
                    +-- Call Auth Service
                    |       |
                    |       +-- Auth Service Span
                    |
                    +-- Call Data Service
                            |
                            +-- Data Service Span
                                    |
                                    +-- Call Database
                                            |
                                            +-- Database Span

All spans sent to TraceCollector
TraceCollector aggregates into complete Trace
```

## Trace Example

```
Trace(trace_7845123, 6 spans, 1.523s)
  Total duration: 1.523s
  Spans: 6
  Span tree:
  └─ frontend.handle_user_request (Frontend) - 1.523s
    └─ call_APIGateway (Frontend) - 1.421s
      └─ APIGateway.handle_request (APIGateway) - 1.321s
        ├─ call_AuthService (APIGateway) - 0.412s
        │   └─ AuthService.handle_request (AuthService) - 0.312s
        └─ call_DataService (APIGateway) - 0.734s
            └─ DataService.handle_request (DataService) - 0.634s
              └─ call_Database (DataService) - 0.223s
                  └─ Database.handle_request (Database) - 0.123s
```

## Context Propagation

### Initial Request

Frontend creates root span:
```python
trace_id = "trace_7845123"
root_span_id = "span_1234567"
parent_span_id = None  # Root has no parent
```

### Downstream Call

Frontend calls API Gateway:
```python
context = TraceContext(
    trace_id="trace_7845123",      # Same trace ID
    span_id="span_2345678",         # New span ID
    parent_span_id="span_1234567"   # Parent is root
)
```

### Further Downstream

API Gateway calls Auth Service:
```python
context = TraceContext(
    trace_id="trace_7845123",      # Still same trace
    span_id="span_3456789",         # New span ID
    parent_span_id="span_2345678"   # Parent is API Gateway's span
)
```

This creates the parent-child tree structure.

## Span Lifecycle

### Creating a Span

```python
span = Span(
    trace_id=context.trace_id,
    span_id=generate_id("span_"),
    parent_span_id=context.span_id,
    operation_name="service.operation",
    service_name="MyService",
    start_time=now
)
```

### Adding Metadata

```python
# Tags for filtering/searching
span.add_tag("http.method", "GET")
span.add_tag("http.url", "/api/users")
span.add_tag("http.status_code", 200)

# Logs for debugging
span.add_log("cache miss")
span.add_log("retrying request", attempt=2)
```

### Finishing a Span

```python
span.finish(end_time)
span.add_tag("success", True)

# Send to collector
await collector.span_queue.put(span)
```

## Performance Analysis

### Identifying Bottlenecks

The trace tree shows where time is spent:

```
Total: 1.523s
  Frontend: 1.523s (includes everything below)
    API Gateway: 1.321s
      Auth: 0.312s (20% of total)
      Data: 0.634s (42% of total) <- BOTTLENECK
        Database: 0.123s
```

The Data Service is the bottleneck—it takes 42% of total time.

### Finding Slow Traces

```python
slow_traces = collector.get_slow_traces(threshold=2.0)
for trace in slow_traces:
    print(f"Slow trace: {trace}")
    # Investigate why this trace was slow
```

## Real-World Applications

### E-Commerce Checkout

```
User Request
  ├─ Frontend
  │   └─ API Gateway
  │       ├─ Cart Service
  │       ├─ Inventory Service
  │       │   └─ Database
  │       └─ Payment Service
  │           └─ Payment Gateway (external)
  └─ Notification Service
```

Trace reveals:
- Payment gateway adds 500ms
- Inventory check only 50ms
- Most time in external API

### Video Streaming

```
Play Request
  ├─ Player Frontend
  │   └─ CDN Selection
  │       ├─ Geo Service
  │       └─ Load Balancer
  │           ├─ Origin Server
  │           │   └─ Storage
  │           └─ Transcoding Service
```

Trace shows:
- CDN selection: 20ms
- Origin fetch: 800ms
- Transcoding: 2000ms <- Need optimization

### Banking Transaction

```
Transfer Request
  ├─ Mobile App
  │   └─ API Gateway
  │       ├─ Authentication
  │       ├─ Fraud Detection
  │       │   ├─ ML Model
  │       │   └─ Rules Engine
  │       ├─ Account Service
  │       │   └─ Ledger Database
  │       └─ Notification Service
```

## Production Considerations

### Sampling Strategies

**Probabilistic Sampling**:
```python
# Sample 10% of traces
if random.random() < 0.1:
    context.sampled = True
```

**Rate-Limited Sampling**:
```python
# Sample 100 traces per second
if traces_this_second < 100:
    context.sampled = True
```

**Adaptive Sampling**:
- Always sample errors
- Always sample slow traces
- Probabilistically sample normal traces

### Storage

Production systems need:
- Time-series database (Cassandra, Elasticsearch)
- Retention policies (keep 7 days, then aggregate)
- Compression (spans are verbose)
- Indexing (by trace ID, service, operation, tags)

### Overhead

Tracing has minimal overhead when done right:
- Span creation: ~1μs
- Context propagation: Add 3 HTTP headers
- Network: Async span submission
- Storage: Only sampled traces

With 10% sampling:
- 90% of requests: Just pass context (negligible)
- 10% of requests: Create and send spans (~100μs)

### Integration

Tracing integrates with:
- **Metrics**: Link slow traces to high latency metrics
- **Logging**: Correlate logs with trace/span IDs
- **Alerting**: Alert on high error rate in traces
- **Profiling**: Deep-dive specific slow spans

## Common Patterns

### Fan-Out

One span spawns multiple parallel children:
```
API Gateway Span
  ├─ User Service (parallel)
  ├─ Order Service (parallel)
  └─ Inventory Service (parallel)
```

### Async Operations

Background jobs create spans:
```
Main Request Span
  └─ Queue Message Span
      └─ Worker Processing Span
```

### External Services

Tag external calls:
```python
span.add_tag("external", True)
span.add_tag("service", "stripe_api")
span.add_tag("http.url", "https://api.stripe.com/charges")
```

## Debugging Workflow

1. **Find slow requests**: Query for traces > SLA threshold
2. **Visualize trace**: See span tree
3. **Identify bottleneck**: Which span takes longest?
4. **Check tags/logs**: What was different about this trace?
5. **Fix issue**: Optimize slow service
6. **Verify**: Compare new traces to baseline

## Further Reading

- [Dapper, a Large-Scale Distributed Systems Tracing Infrastructure](https://research.google.com/pubs/pub36356.html)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Zipkin Architecture](https://zipkin.io/pages/architecture.html)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Distributed Tracing in Practice](https://www.oreilly.com/library/view/distributed-tracing-in/9781492056621/)
