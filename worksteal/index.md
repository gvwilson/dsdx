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
This design minimizes [contention](g:contention) while providing some [load balancing](g:load-balancing),
and appears throughout high-performance computing.
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

## The Scheduler {: #worksteal-scheduler}

The scheduler coordinates workers and provides task submission:

<div data-inc="scheduler.py" data-filter="inc=scheduler"></div>

We can create a simple simulation with load imbalance to see it in action:

<div data-inc="ex_basic_ws.py" data-filter="inc=sim"></div>

The output shows workers executing tasks and stealing from each other when they run out of local work.
The steal rate shows how much load balancing occurred:

<div data-inc="ex_basic_ws.txt" data-filter="head=10 + tail=7"></div>

## Nested Task Spawning {: #worksteal-spawn}

A common extension of work-stealing is
to support [divide-and-conquer](g:divide-and-conquer) algorithms
by allowing tasks to spawn subtasks.
To explore this,
we can create a task generator:

<div data-inc="task_generator.py" data-filter="inc=gen"></div>

and then create a worker that spawns subtasks with some random probability
(in our case, 30%):

<div data-inc="worker_with_spawning.py" data-filter="inc=spawner"></div>

The final step is to write a scheduler that creates these workers:

<div data-inc="scheduler_with_spawning.py" data-filter="inc=gen"></div>

Our simulation looks similar to our first one:

<div data-inc="ex_spawning.py" data-filter="inc=sim"></div>

Its output shows that spawning helps balance the load
even with irregular task creation:

<div data-inc="ex_spawning.txt" data-filter="head=20 + tail=8"></div>

## Load Balancing Strategies {: #worksteal-balance}

What effect does target selection strategy have on performance?
To find out,
we can create a worker that uses adaptive target selection,
i.e.,
that steals tasks from the largest of its peers' queues:

<div data-inc="adaptive_worker.py" data-filter="inc=worker"></div>

Unsurprisingly,
this leads to better load balancing:

<div data-inc="ex_adaptive.txt" data-filter="head=20 + tail=8"></div>

## Task Granularity {: #worksteal-granularity}

The [granularity](g:granularity) of tasks—i.e.,
how much work is in each one—has a big impact on performance.
Many small tasks create lots of scheduling overhead,
while a few large tasks cause load imbalance.
Using the code we have written so far,
we can easily experiment with the effect of changing task size:

<div data-inc="ex_granularity.txt"></div>

Our implementations demonstrate the core concepts of work stealing,
but production systems go further.
In particular,
they try to prevent [livelock](g:livelock) by limiting how long a worker searches for victims,
and use exponential backoff rather than spinning continuously when trying to steal work.

## Exercises {: #worksteal-exercises}

FIXME: add exercises.
