import random
from tracing_types import SamplingStrategy


class Sampler:
    """Sampling strategy for traces."""

    def __init__(self, strategy: SamplingStrategy, sample_rate: float = 0.1) -> None:
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
            return self.traces_sampled % int(1 / self.sample_rate) == 0

        return False
