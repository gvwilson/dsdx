"""MapReduce coordinator with combiner optimization."""

from asimpy import Environment
from typing import Callable, Optional
from mapreduce_coordinator import MapReduceCoordinator


class MapReduceCoordinatorWithCombiner(MapReduceCoordinator):
    """Coordinator with combiner support."""
    
    def __init__(self, env: Environment, 
                 map_fn: Callable, 
                 reduce_fn: Callable,
                 combiner_fn: Optional[Callable] = None,
                 num_reducers: int = 3):
        super().__init__(env, map_fn, reduce_fn, num_reducers)
        self.combiner_fn = combiner_fn or reduce_fn
