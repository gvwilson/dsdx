# A Work-Stealing Scheduler

How do you distribute work
When you have hundreds or thousands of tasks to execute and a handful of CPU cores?
A naïve approach is to use a single queue,
but this creates a bottleneck,
since every worker must compete for access to that queue.

A [work-stealing](g:work-stealing) scheduler solves this problem through decentralization.
Each worker maintains a local [deque](g:deque) of tasks.
Workers execute tasks from one end of their own deque,
but if a worker runs out of tasks it can take some from the other end of another worker's deque.
This design minimizes [contention](g:contention) while providing some [load balancing](g:load-balancing).

This pattern appears throughout high-performance computing:
[Go's runtime scheduler][go-scheduler] uses is to distribute goroutines across threads,
Java's [fork/join framework][java-fork-join] enables parallel divide-and-conquer algorithms,
and [Tokio][tokio] (Rust's async runtime) uses it to schedule [futures](g:future) across worker threads.

## The Work-Stealing Pattern {: #worksteal-pattern}

A work-stealing system has five parts:

1.  Each worker has a local deque of tasks.
1.  Those tasks are independent of each other.
1.  Workers pop tasks from the private end of their deque.
1.  Idle workers take tasks from the public end of other workers' deques.
1.  Running tasks can create new child tasks.

The key idea is asymmetry:
the owning worker operates on one end of their deque
(usually called the bottom)
while other workers (called thieves) steal from its other end (the top).
This reduces contention because owners and thieves don't compete for the same task
unless the queue is almost empty.

Let's start with the task representation:

<div data-inc="task.py" data-filter="inc=task"></div>

Each task has an ID,
a duration to simulate CPU-bound work,
and an optional parent task ID for tracking task dependencies.

Each worker maintains a deque.
In our simulation, we'll use a simple list-based deque:

<div data-inc="worker_deque.py" data-filter="inc=deque"></div>

A production system would use something more sophisticated than a simple Python list
to manage the deque,
but our simulation focuses on the algorithmic pattern rather than low-level synchronization.

A worker executes tasks from its local deque and steals when idle.
We start by setting up its members:

<div data-inc="worker.py" data-filter="inc=deque"></div>

and then define its behavior:

<div data-inc="worker.py" data-filter="inc=run"></div>

As the code above shows,
the worker continuously tries to execute tasks.
If its local deque is empty,
it attempts to steal from other workers.
If stealing fails,
it waits briefly before trying again.

Executing a task is relatively straightforward:

<div data-inc="worker.py" data-filter="inc=execute"></div>

Stealing a task from another worker is somewhat more interesting.
The most important part is that we randomize the order in which we check the workers
in order to spread the load as evenly as possible:

<div data-inc="worker.py" data-filter="inc=steal"></div>

## Scheduler {: #worksteal-scheduler}

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

## Basic Simulation {: #worksteal-sim}

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

## Nested Task Spawning {: #worksteal-spawn}

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

## Load Balancing Strategies {: #worksteal-balance}

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

## Task Granularity and Performance {: #worksteal-perf}

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

## Real-World Considerations {: #worksteal-real}

Our implementation demonstrates core concepts, but production work-stealing schedulers need:

-   **Lock-free deques**: Use atomic compare-and-swap operations instead of locks.
The [Chase-Lev deque][chase-lev-deque] is a popular choice.

-   **Bounded stealing attempts**: Prevent livelock by limiting how long a worker searches for victims.

-   **NUMA awareness**: On multi-socket systems, prefer stealing from nearby workers to maintain cache locality.

-   **Priority queues**: Some tasks are more important than others and should execute first.

-   **Backoff strategies**: Idle workers should back off exponentially rather than spinning continuously.

-   **Work affinity**: Tasks that share data should execute on the same worker when possible.

-   **Termination detection**: Determining when all work is complete in a distributed system is non-trivial.
