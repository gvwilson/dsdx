"""Decorators for automatic distributed tracing instrumentation."""

from functools import wraps
from typing import Any, Callable
from tracing_types import Span, TraceContext, generate_id


# mccole: storage
_current_context = None
_current_collector = None


def set_trace_context(context: TraceContext) -> None:
    """Set the current trace context."""
    global _current_context
    _current_context = context


def get_trace_context() -> TraceContext | None:
    """Get the current trace context."""
    return _current_context


def set_collector(collector) -> None:
    """Set the trace collector."""
    global _current_collector
    _current_collector = collector


def get_collector():
    """Get the trace collector."""
    return _current_collector
# mccole: /storage


# mccole: traced
def traced(operation_name: str):
    """Decorator that automatically creates spans for functions."""

    def decorator(func: Callable) -> Callable:
        # Get operation name
        op_name = operation_name
        
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Get current context
            context = get_trace_context()
            if not context or not context.sampled:
                # No tracing, just call function
                return await func(self, *args, **kwargs)
            
            # Get service name from self
            service_name = getattr(self, "service_name", self.__class__.__name__)
            
            # Create span
            span = Span(
                trace_id=context.trace_id,
                span_id=generate_id("span_"),
                parent_span_id=context.span_id,
                operation_name=op_name,
                service_name=service_name,
                start_time=self.now,
            )
            
            # Save old context and set new one
            old_context = get_trace_context()
            new_context = TraceContext(
                trace_id=context.trace_id,
                span_id=span.span_id,
                parent_span_id=context.span_id,
                sampled=True,
            )
            set_trace_context(new_context)
            
            try:
                # Call function
                result = await func(self, *args, **kwargs)
                span.add_tag("success", True)
                return result
                
            except Exception as e:
                # Record error
                span.add_tag("error", True)
                span.add_tag("error.message", str(e))
                span.add_log("exception", exception=str(e))
                raise
                
            finally:
                # Finish span and send to collector
                span.finish(self.now)
                collector = get_collector()
                if collector:
                    collector.span_queue.put(span)
                
                # Restore old context
                set_trace_context(old_context)
        
        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            # For sync functions, just add tags but don't trace
            return func(self, *args, **kwargs)
        
        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
# mccole: /traced


# mccole: tag
def add_tag(key: str, value: Any) -> None:
    """Add a tag to the current span.
    
    This is a convenience function for adding tags within traced functions.
    """
    # Tags would be stored in thread-local span if we tracked that
    # For now, this is a placeholder showing the API
    pass
# mccole: /tag


# mccole: log
def add_log(message: str, **fields: Any) -> None:
    """Add a log entry to the current span.
    
    This is a convenience function for adding logs within traced functions.
    """
    # Logs would be stored in thread-local span if we tracked that
    # For now, this is a placeholder showing the API
    pass
# mccole: /log
