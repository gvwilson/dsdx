# Distributed Tracing

If a monolithic application is slow,
we can profile a single process to find out why.
In a [microservices](g:microservice) architecture,
however,
a single request may touch many services,
each of which may cause multiple database queries and external API calls.
This makes it a lot harder to figure out exactly what's going on.

Distributed tracing solves this by tracking requests as they flow through the system.
A tracing systems assigns each request a unique ID,
which that request carries through every service it touches.
Each service operation records the work it does
along with timing information and other metadata.
Collecting and combining these records allows the tracing framework
to understand dependencies between services
and identify bottlenecks.

Distributed tracing has two key elements:

-   A [span](g:span) represents a single unit of work.
    Spans form a tree with its origin in a [root span](g:root-span);
    this tree represents the (distributed) call graph.

-   A [trace](g:trace) is complete journey of a request through the system,
    and is identified by a unique trace ID.
    A single trace may contain many spans.

[Context propagation](g:context-propagation) means
passing trace and span IDs between services so that they can be correlated.
Trace and span IDs are often propagated using [HTTP headers](g:http-header):

```
X-Trace-Id: abc123
X-Span-Id: def456
X-Parent-Span-Id: ghi789
```

Tracing systems often use [sampling](g:sampling)
to record only a fraction of traces.
Doing this means that some questions cannot be answered after the fact,
but sampling reduces storage costs and,
more importantly,
prevents the tracing system from overwhelming the network.

Finally, tags and logs are metadata attached to spans for debugging.
Tags are values used for filtering and searching,
such as the [HTTP status code](g:http-status-code),
while logs are timestamped events such as a [cache miss](g:cache-miss)
or retry attempt.

## A Minimum Viable Decorator {: #tracing-decorator}

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

A minimum viable version of that decorator needs to do the following:

1.  Check for active traces.
    If no trace context exists or sampling is disabled,
    it just calls the function normally.
2.  Create a child span whose parent is the current span (if there is one).
3.  Propagate trace context for nested calls.
4.  Handle errors, i.e., catch exceptions and tag spans with error information.
5.  Clean up by finishing the current span and restoring the previous context.

None of this is particularly hard,
but it does require a fair bit of code.
First,
we create a [singleton](g:singleton) to hold the active trace context
and the [collector](g:trace-collector) where completed spans are to be sent.
(In production,
we would use [thread-local storage](g:thread-local-storage)
or [async context variables](g:async-context-vars) to storage this data.)

<div data-inc="tracing_decorators.py" data-filter="inc=storage"></div>

We can now define the tracing decorator itself.
It's long,
but all of the steps are fairly straightforward:

<div data-inc="tracing_decorators.py" data-filter="inc=traced"></div>

## Data Types {: #tracing-types}

We now need to double back and define the core types for distributed tracing.
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

The output shows that we are capturing what we wanted to:

<div data-inc="ex_decorators.txt"></div>

## Useful Data {: #tracing-useful}

The code we just built commits a cardinal sin:
it generates data in an undocumented, hard-to-parse ASCII format.
In most cases trace data will be consumed by other programs,
which will summarize and reorganize it
to make it comprehensible to human beings.
To support that,
we should always generate data in a structured format such as JSON,
and use a standard [schema](g:schema) instead of creating one of our own.

The [OpenTelemetry][opentelemetry] standard defines such a schema,
but it is notoriously complex.
The simplified subset generated by `json_collector.py` has:

-   a single resource per trace (OpenTelemetry supports multiple);
-   a single scope per resource (again, OpenTelemetry supports multiple);
-   one kind of span instead of the six that OpenTelemetry offers;
-   no links between spans; and
-   simplified status codes.

Even with these simplifications,
a simple example like the one below produces over 300 lines of pretty-printed output:

<div data-inc="ex_json.py" data-filter="inc=client"></div>

A sample clause of this JSON looks like this:

<div data-inc="ex_json.txt" data-filter="head=52"></div>

It isn't something anyone would browse for fun,
but (hopefully) everything needed to track down problems is there.

## Exercises {: #tracing-exercises}

FIXME: add exercises.
