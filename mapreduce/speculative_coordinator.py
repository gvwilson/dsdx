"""MapReduce coordinator with speculative execution."""

from asimpy import Environment, Process
from typing import Callable, Dict
from mapreduce_coordinator import MapReduceCoordinator


class StragglerMonitor(Process):
    """Monitor for slow tasks and launch speculative copies."""
    
    def init(self, coordinator: 'SpeculativeCoordinator'):
        self.coordinator = coordinator
    
    async def run(self):
        """Monitor for stragglers."""
        while not self.coordinator.map_phase_complete:
            await self.timeout(1.0)
            await self.coordinator._check_for_stragglers()


class SpeculativeCoordinator(MapReduceCoordinator):
    """Coordinator with speculative execution for stragglers."""
    
    def __init__(self, env: Environment, 
                 map_fn: Callable, 
                 reduce_fn: Callable,
                 num_reducers: int = 3,
                 speculative_threshold: float = 5.0):
        super().__init__(env, map_fn, reduce_fn, num_reducers)
        self.speculative_threshold = speculative_threshold
        self.task_start_times: Dict[str, float] = {}
        self.speculative_tasks: set = set()
    
    async def _dispatch_map_tasks(self):
        """Dispatch map tasks with speculative execution."""
        await super()._dispatch_map_tasks()
        
        # Start monitoring for stragglers
        StragglerMonitor(self.env, self)
    
    async def _check_for_stragglers(self):
        """Launch speculative tasks for stragglers."""
        now = self.env.now
        
        for task in self.pending_map_tasks:
            if task.task_id in self.completed_map_tasks:
                continue
            
            if task.task_id not in self.task_start_times:
                self.task_start_times[task.task_id] = now
                continue
            
            elapsed = now - self.task_start_times[task.task_id]
            
            if (elapsed > self.speculative_threshold and 
                task.task_id not in self.speculative_tasks):
                
                print(f"[{now:.1f}] Launching speculative copy of {task.task_id}")
                self.speculative_tasks.add(task.task_id)
                
                # Launch backup copy
                worker = self._get_available_worker()
                await worker.task_queue.put(task)
