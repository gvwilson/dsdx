# Work-Stealing Scheduler

Modern programs need to efficiently utilize multiple CPU cores to achieve high performance.
When you have hundreds or thousands of tasks to execute and a handful of CPU cores,
how do you distribute the work?
A naive approach would use a central queue: workers pull tasks from one end,
and new tasks are added to the other.
But this creates a bottleneck—every worker must compete for access to the shared queue.

Work-stealing schedulers solve this problem through decentralization.
Each worker maintains its own local deque (double-ended queue) of tasks.
Workers execute tasks from one end of their own deque,
but when a worker runs out of work
it can "steal" tasks from the other end of another worker's deque.
This design minimizes contention—workers mostly operate on their own queues,
only interacting when load balancing is needed.

This pattern appears throughout high-performance computing:
[Go's runtime scheduler][go-scheduler] uses work-stealing to distribute goroutines across threads,
[Java's Fork/Join framework][java-fork-join] enables parallel divide-and-conquer algorithms,
and [Tokio][tokio] (Rust's async runtime) schedules futures across worker threads.
Understanding work-stealing is essential for writing efficient parallel programs.

## The Work-Stealing Pattern

In a work-stealing system, we have:

1.  **Workers**: Each worker has a local deque of tasks
1.  **Tasks**: Units of work that can be executed independently
1.  **Local execution**: Workers pop tasks from the "private" end of their deque
1.  **Stealing**: Idle workers steal tasks from the "public" end of other workers' deques
1.  **Task spawning**: Running tasks can create new child tasks

The key insight is asymmetry: the owning worker operates on one end (the "bottom") while thieves steal from the other end (the "top").
This reduces contention because the owner and thieves usually don't compete for the same task.

## Our Implementation

We'll build a work-stealing scheduler using asimpy.
Our simulation will show how tasks are distributed, how stealing balances load, and how nested task creation (a task spawning child tasks) works naturally.

Let's start with the task representation:

```python
from asimpy import Environment, Process, Queue
from typing import List, Optional, Callable, Any
from dataclasses import dataclass
import random


@dataclass
class Task:
    """A unit of work to be executed."""
    task_id: str
    work_duration: float
    parent_id: Optional[str] = None  # For nested tasks
    
    def __str__(self):
        return f"Task({self.task_id})"
```

Each task has an ID, a duration (simulating CPU-bound work), and optionally a parent task ID for tracking task dependencies.

## Worker Deques

Each worker maintains a deque.
In our simulation, we'll use a simple list-based deque:

```python
class WorkerDeque:
    """Double-ended queue for tasks with stealing support."""
    
    def __init__(self):
        self.tasks: List[Task] = []
    
    def push_bottom(self, task: Task):
        """Owner pushes task to bottom (private end)."""
        self.tasks.append(task)
    
    def pop_bottom(self) -> Optional[Task]:
        """Owner pops task from bottom."""
        if not self.tasks:
            return None
        return self.tasks.pop()
    
    def steal_top(self) -> Optional[Task]:
        """Thief steals task from top (public end)."""
        if not self.tasks:
            return None
        return self.tasks.pop(0)
    
    def is_empty(self) -> bool:
        """Check if deque is empty."""
        return len(self.tasks) == 0
    
    def size(self) -> int:
        """Return number of tasks."""
        return len(self.tasks)
```

In production systems, this would use atomic operations and careful memory ordering to avoid locks.
Our simulation focuses on the algorithmic pattern rather than low-level synchronization.

## Worker Implementation

A worker executes tasks from its local deque and steals when idle:

```python
class Worker(Process):
    """Worker that executes tasks with work-stealing."""
    
    def init(self, worker_id: int, scheduler: 'WorkStealingScheduler'):
        self.worker_id = worker_id
        self.scheduler = scheduler
        self.deque = WorkerDeque()
        self.tasks_executed = 0
        self.tasks_stolen = 0
        self.current_task: Optional[Task] = None
        
    async def run(self):
        """Main worker loop: execute local tasks or steal."""
        while True:
            # Try to get a task from local deque
            task = self.deque.pop_bottom()
            
            if task:
                # Execute local task
                await self.execute_task(task)
            else:
                # No local work, try stealing
                stolen = await self.try_steal()
                
                if stolen:
                    await self.execute_task(stolen)
                else:
                    # No work available anywhere, wait a bit
                    await self.timeout(0.1)
    
    async def execute_task(self, task: Task):
        """Execute a task."""
        self.current_task = task
        self.tasks_executed += 1
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Executing {task.task_id} (queue size: {self.deque.size()})")
        
        # Simulate work
        await self.timeout(task.work_duration)
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Completed {task.task_id}")
        
        self.current_task = None
    
    async def try_steal(self) -> Optional[Task]:
        """Try to steal a task from another worker."""
        # Random victim selection
        victims = [w for w in self.scheduler.workers if w != self]
        
        if not victims:
            return None
        
        # Shuffle to avoid patterns
        random.shuffle(victims)
        
        for victim in victims:
            task = victim.deque.steal_top()
            if task:
                self.tasks_stolen += 1
                print(f"[{self.now:.1f}] Worker {self.worker_id}: "
                      f"Stole {task.task_id} from Worker {victim.worker_id}")
                return task
        
        return None
    
    def spawn_task(self, task: Task):
        """Spawn a new task (called by executing task)."""
        self.deque.push_bottom(task)
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Spawned {task.task_id}")
```

The worker continuously tries to execute tasks.
If its local deque is empty, it attempts to steal from other workers.
If stealing fails, it waits briefly before trying again.

## Scheduler

The scheduler coordinates workers and provides task submission:

```python
class WorkStealingScheduler:
    """Scheduler that coordinates work-stealing workers."""
    
    def __init__(self, env: Environment, num_workers: int):
        self.env = env
        self.num_workers = num_workers
        self.workers: List[Worker] = []
        self.task_counter = 0
        
        # Create workers
        for i in range(num_workers):
            worker = Worker(env, i, self)
            self.workers.append(worker)
    
    def submit_task(self, work_duration: float, 
                   parent_id: Optional[str] = None) -> Task:
        """Submit a task to a random worker."""
        self.task_counter += 1
        task = Task(
            task_id=f"T{self.task_counter}",
            work_duration=work_duration,
            parent_id=parent_id
        )
        
        # Assign to random worker (could use other strategies)
        worker = random.choice(self.workers)
        worker.deque.push_bottom(task)
        
        print(f"[{self.env.now:.1f}] Submitted {task.task_id} "
              f"to Worker {worker.worker_id}")
        
        return task
    
    def get_statistics(self):
        """Get scheduler statistics."""
        total_executed = sum(w.tasks_executed for w in self.workers)
        total_stolen = sum(w.tasks_stolen for w in self.workers)
        
        print("\n=== Statistics ===")
        print(f"Total tasks executed: {total_executed}")
        print(f"Total tasks stolen: {total_stolen}")
        print(f"Steal rate: {100 * total_stolen / max(total_executed, 1):.1f}%")
        
        for worker in self.workers:
            print(f"Worker {worker.worker_id}: "
                  f"executed={worker.tasks_executed}, "
                  f"stolen={worker.tasks_stolen}, "
                  f"queue={worker.deque.size()}")
```

## Basic Simulation

Let's create a simple simulation with load imbalance to see stealing in action:

```python
def run_basic_simulation():
    """Basic work-stealing simulation."""
    env = Environment()
    
    # Create scheduler with 3 workers
    scheduler = WorkStealingScheduler(env, num_workers=3)
    
    # Submit tasks with varying durations
    for i in range(10):
        scheduler.submit_task(work_duration=random.uniform(0.5, 2.0))
    
    # Run simulation
    env.run(until=20)
    
    # Print statistics
    scheduler.get_statistics()


if __name__ == "__main__":
    run_basic_simulation()
```

When you run this, you'll see workers executing tasks and stealing from each other when they run out of local work.
The steal rate shows how much load balancing occurred.

## Nested Task Spawning

One powerful feature of work-stealing is handling nested parallelism—tasks that create subtasks.
This is the foundation of parallel divide-and-conquer algorithms:

```python
class TaskGenerator(Process):
    """Generates tasks including ones that spawn subtasks."""
    
    def init(self, scheduler: WorkStealingScheduler, 
             num_initial_tasks: int):
        self.scheduler = scheduler
        self.num_initial_tasks = num_initial_tasks
    
    async def run(self):
        """Generate initial tasks."""
        for i in range(self.num_initial_tasks):
            task = self.scheduler.submit_task(
                work_duration=random.uniform(1.0, 3.0)
            )
            await self.timeout(0.5)


class WorkerWithSpawning(Worker):
    """Worker that can spawn child tasks during execution."""
    
    async def execute_task(self, task: Task):
        """Execute task and possibly spawn children."""
        self.current_task = task
        self.tasks_executed += 1
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Executing {task.task_id}")
        
        # Do half the work
        await self.timeout(task.work_duration / 2)
        
        # Randomly spawn child tasks (simulating divide-and-conquer)
        if random.random() < 0.3:  # 30% chance
            num_children = random.randint(1, 3)
            for i in range(num_children):
                child = Task(
                    task_id=f"{task.task_id}.{i}",
                    work_duration=random.uniform(0.3, 1.0),
                    parent_id=task.task_id
                )
                self.spawn_task(child)
        
        # Finish the work
        await self.timeout(task.work_duration / 2)
        
        print(f"[{self.now:.1f}] Worker {self.worker_id}: "
              f"Completed {task.task_id}")
        
        self.current_task = None


class SchedulerWithSpawning(WorkStealingScheduler):
    """Scheduler using workers that can spawn tasks."""
    
    def __init__(self, env: Environment, num_workers: int):
        self.env = env
        self.num_workers = num_workers
        self.workers: List[WorkerWithSpawning] = []
        self.task_counter = 0
        
        # Create workers with spawning capability
        for i in range(num_workers):
            worker = WorkerWithSpawning(env, i, self)
            self.workers.append(worker)


def run_spawning_simulation():
    """Demonstrate nested task spawning."""
    env = Environment()
    
    # Create scheduler with spawning workers
    scheduler = SchedulerWithSpawning(env, num_workers=4)
    
    # Generate initial tasks
    generator = TaskGenerator(env, scheduler, num_initial_tasks=5)
    
    # Run simulation
    env.run(until=30)
    
    # Print statistics
    scheduler.get_statistics()
```

This simulation shows how tasks can spawn children, which are added to the local deque and may be stolen by other workers.
This naturally balances load even with irregular task creation patterns.

## Load Balancing Strategies

Different victim selection strategies affect performance:

```python
class AdaptiveWorker(Worker):
    """Worker with adaptive victim selection."""
    
    def init(self, worker_id: int, scheduler: 'WorkStealingScheduler'):
        super().init(worker_id, scheduler)
        self.steal_attempts = 0
        self.failed_steals = 0
    
    async def try_steal(self) -> Optional[Task]:
        """Try to steal with adaptive victim selection."""
        self.steal_attempts += 1
        
        # Try workers with largest queues first
        victims = [w for w in self.scheduler.workers if w != self]
        victims.sort(key=lambda w: w.deque.size(), reverse=True)
        
        for victim in victims:
            if victim.deque.size() > 0:
                task = victim.deque.steal_top()
                if task:
                    self.tasks_stolen += 1
                    print(f"[{self.now:.1f}] Worker {self.worker_id}: "
                          f"Stole {task.task_id} from Worker {victim.worker_id} "
                          f"(victim queue: {victim.deque.size()})")
                    return task
        
        self.failed_steals += 1
        return None


class AdaptiveScheduler(WorkStealingScheduler):
    """Scheduler with adaptive workers."""
    
    def __init__(self, env: Environment, num_workers: int):
        self.env = env
        self.num_workers = num_workers
        self.workers: List[AdaptiveWorker] = []
        self.task_counter = 0
        
        for i in range(num_workers):
            worker = AdaptiveWorker(env, i, self)
            self.workers.append(worker)


def run_adaptive_simulation():
    """Demonstrate adaptive stealing strategy."""
    env = Environment()
    
    scheduler = AdaptiveScheduler(env, num_workers=4)
    
    # Create imbalanced initial load
    for i in range(15):
        # Give most tasks to worker 0
        worker_idx = 0 if i < 12 else random.randint(0, 3)
        scheduler.workers[worker_idx].deque.push_bottom(
            Task(f"T{i+1}", random.uniform(1.0, 2.0))
        )
    
    env.run(until=25)
    scheduler.get_statistics()
```

The adaptive strategy targets victims with the most work, leading to faster load balancing.

## Task Granularity and Performance

Task granularity—how much work each task does—significantly affects performance.
Too fine-grained, and scheduling overhead dominates; too coarse-grained, and load imbalance reduces parallelism:

```python
class PerformanceAnalyzer(Process):
    """Analyzes scheduler performance with different granularities."""
    
    def init(self, scheduler: WorkStealingScheduler, 
             total_work: float, task_granularity: float):
        self.scheduler = scheduler
        self.total_work = total_work
        self.task_granularity = task_granularity
        self.start_time = None
        self.end_time = None
    
    async def run(self):
        """Submit tasks and measure completion time."""
        self.start_time = self.now
        
        num_tasks = int(self.total_work / self.task_granularity)
        
        print(f"\n[{self.now:.1f}] Starting: {num_tasks} tasks "
              f"of {self.task_granularity}s each")
        
        for i in range(num_tasks):
            self.scheduler.submit_task(self.task_granularity)
        
        # Wait for all workers to become idle
        while True:
            await self.timeout(1.0)
            
            all_idle = all(
                w.deque.is_empty() and w.current_task is None
                for w in self.scheduler.workers
            )
            
            if all_idle:
                self.end_time = self.now
                break
        
        elapsed = self.end_time - self.start_time
        speedup = self.total_work / elapsed
        efficiency = speedup / self.scheduler.num_workers
        
        print(f"\n=== Performance Analysis ===")
        print(f"Granularity: {self.task_granularity}s")
        print(f"Total work: {self.total_work}s")
        print(f"Wall time: {elapsed:.2f}s")
        print(f"Speedup: {speedup:.2f}x")
        print(f"Efficiency: {efficiency:.1%}")


def run_granularity_experiment():
    """Experiment with different task granularities."""
    for granularity in [0.1, 0.5, 2.0]:
        print(f"\n{'='*60}")
        print(f"Testing granularity: {granularity}s")
        print('='*60)
        
        env = Environment()
        scheduler = WorkStealingScheduler(env, num_workers=4)
        
        analyzer = PerformanceAnalyzer(
            env, scheduler, 
            total_work=20.0, 
            task_granularity=granularity
        )
        
        env.run(until=50)
        scheduler.get_statistics()
```

This experiment shows how granularity affects speedup and efficiency.
Fine-grained tasks enable better load balancing but increase overhead.

## Real-World Considerations

Our implementation demonstrates core concepts, but production work-stealing schedulers need:

-   **Lock-free deques**: Use atomic compare-and-swap operations instead of locks.
The [Chase-Lev deque][chase-lev-deque] is a popular choice.

-   **Bounded stealing attempts**: Prevent livelock by limiting how long a worker searches for victims.

-   **NUMA awareness**: On multi-socket systems, prefer stealing from nearby workers to maintain cache locality.

-   **Priority queues**: Some tasks are more important than others and should execute first.

-   **Backoff strategies**: Idle workers should back off exponentially rather than spinning continuously.

-   **Work affinity**: Tasks that share data should execute on the same worker when possible.

-   **Termination detection**: Determining when all work is complete in a distributed system is non-trivial.

## Conclusion

Work-stealing schedulers achieve efficient load balancing through decentralization.
Each worker operates mostly independently, reducing contention.
Stealing provides dynamic load balancing without central coordination.
The key principles are:

1.  **Local deques** minimize contention between workers
1.  **Asymmetric access** (bottom vs. top) reduces conflicts
1.  **Random victim selection** prevents pathological patterns
1.  **Task spawning** naturally supports divide-and-conquer algorithms
1.  **Granularity** must balance overhead against load balancing
