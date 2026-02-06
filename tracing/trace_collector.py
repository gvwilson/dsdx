"""Trace collector for aggregating spans into traces."""

from asimpy import Process, Queue
from typing import Dict, List
from tracing_types import Span, Trace


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
        print(f"  Total duration: {duration:.3f}s" if duration else "  Duration: unknown")
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
