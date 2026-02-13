# Distributed Tracing

If a monolithic application is slow,
we can profile a single process to find out why.
In a [microservices](g:microservice) architecture,
however,
a single request may touch dozens of services,
each of which may cause multiple database queries and external API calls.
This makes it a lot harder to figure out exactly what's going on.

Distributed tracing solves this by tracking requests as they flow through the system.
It works by assigning each request a unique ID and tracking it through every service it touches.
Each service operation creates a [span](g:span) to record the work it does
along with timing information and other metadata.
Collecting and combining these spans allows the tracing framework
to understand dependencies between services
and identify bottlenecks.

Distributed tracing has several key abstractions:

-   A [trace](g:trace) is complete journey of a request through the system,
    and is identified by a unique trace ID.

-   A span represents a single unit of work.
    Spans form a tree representing the (distributed) call graph.

-   [Context propagation](g:context-propagation) means
    passing trace and span IDs between services so that they can be correlated.

-   [Sampling](g:sampling)
    is the practice of recording only a fraction of traces to reduce overhead and storage costs.

-   Finally, tags and logs are metadata attached to spans for debugging.
    Tags are values used for filtering and searching,
    such as the [HTTP status code](g:http-status-code),
    while logs are timestamped events such as a [cache miss](g:cache-miss)
    or retry attempt.

<div class="callout" markdown="1">

Spans have parent-child relationships, forming a tree;
the root span is the only one without a parent.
A trace may contain many spans.
Trace and span IDs are often propagated as [HTTP headers](g:http-header):

```
X-Trace-Id: abc123
X-Span-Id: def456
X-Parent-Span-Id: ghi789
```

</div>

Suppose we want to write a method `handle_request()`
that performs some work in `do_work()`
in a traceable way.
If we add the tracing code directly in `handle_request()`
we wind up with something like this:

<div data-inc="long_winded.py" data-filter="inc=service"></div>

That is 15 lines of tracing code for a simple function,
and those lines would have to be copied into every function we want to trace.
A better approach is to define a [decorator](g:decorator)
that adds tracing for us so that we can write:

<div data-inc="short_winded.py" data-filter="inc=service"></div>

## A Minimum Viable Decorator {: #tracing-decorator}

A minimum viable version of that decorator needs to do the following:

1.  Check for active traces.
    If no trace context exists or sampling is disabled, it just calls the function normally.
2.  Create a child span using the current span as a parent.
3.  Propagate trace context for nested calls.
4.  Handle errors, i.e., catch exceptions and tag spans with error information.
5.  Clean up by finishing the current span and restoring the previous context.

None of this is particularly hard,
but it takes almost 80 lines to do it all:

<div data-inc="tracing_decorators.py" data-filter="inc=traced"></div>

## Storing Data {: #tracing-storage}

The decorator uses module-level variables to keep track of things.
`_current_context` holds the active trace context,
while `_current_collector` is where to send completed spans:

<div data-inc="tracing_decorators.py" data-filter="inc=storage"></div>

In production,
we would use [thread-local storage](g:thread-local-storage)
or [async context variables](g:async-context-vars) instead of globals.

## Data Types {: #tracing-types}

Let's define the core types for distributed tracing.
`TraceContext` propagates between services:

<div data-inc="tracing_types.py" data-filter="inc=context"></div>

`Span` tracks individual operations,
and has methods for adding tags and log entries
and to mark the span as completed:

<div data-inc="tracing_types.py" data-filter="inc=span"></div>

Finally, `Trace` aggregates spans,
and has methods for adding spans and getting the overall duration of the trace:

<div data-inc="tracing_types.py" data-filter="inc=trace"></div>

## Trace Collector

The collector is an active process
that receives spans from services and assembles them into traces.
When it runs,
it repeatedly gets a span from its incoming queue and processes it:

<div data-inc="trace_collector.py" data-filter="inc=collector"></div>

To process a new span,
the collector either adds it to an existing trace
or creates a new one.
If the trace is now complete,
the collector moves it from the active set into the completed set:

<div data-inc="trace_collector.py" data-filter="inc=process"></div>

## A Simple Service {: #tracing-service}

With all this machinery in place,
tracing a microservice is relatively straightforward:

<div data-inc="simple_service.py" data-filter="inc=simple"></div>

`handle_request` is automatically traced;
`process_data` is also traced and becomes a child span.
No spans are created manually,
and error handling is automatic.

The client creates the root span manually (since it initiates the trace):

<div data-inc="ex_decorators.py" data-filter="inc=client"></div>

The output is verbose:

<div data-inc="ex_decorators.txt"></div>

## Exercises {: #tracing-exercises}

FIXME: add exercises.
