# Discrete Event Simulation with asimpy

<p class="subtitle" markdown="1">a short introduction to our toolbox</p>

Discrete event simulation (DES) simulates systems in which events occur at discrete points in time.
The simulation maintains a virtual clock and executes events in chronological order.
Unlike real-time systems,
the simulation jumps directly from one event time to the next,
skipping empty intervals.
(Time steps are often referred to as "ticks".)

## Async/Await

Python's `async`/`await` syntax enables cooperative multitasking without threads.
Functions defined as `async def` return coroutine objects when called.
These coroutines can be paused at `await` points and later resumed.
More specifically,
when a coroutine executes `value = await expr`, it:

1.  yields the awaited object `expr` to its caller;
2.  suspends execution at that point;
3.  resumes later when `send(value)` is called on it; an thend
4.  returns the value passed to `send()` as the result of the `await` expression
    inside the resumed coroutine.

[asimpy][asimpy] uses this mechanism to pause and resume coroutines to simulate simultaneously execution.
This is similar to the `yield`-based mechanism used in [SimPy][simpy].

## `Environment`: Process and Event Management

The `Environment` class maintains the simulation state.
`Environment.schedule(time, callback)` adds a callback to the queue,
where it is given a serial number
to ensure deterministic ordering when multiple events occur at the same time.

`Environment.run()` implements the main simulation loop:

1.  Extract the next pending event from the priority queue.
2.  If an `until` parameter is specified and the event time exceeds it, stop.
3.  Otherwise, execute the callback to perform the next simulated action.

## `Process`: Active Entities

`Process` is the base class for simulation processes.
(Unlike [SimPy][simpy], [asimpy][asimpy] uses a class rather than bare coroutines.)
Users define the behavior of their processes by implementing the `run()` method.
When a `Process` is constructed, it:

1.  stores a reference to the simulation environment;
2.  calls `init()` for subclass-specific setup
    (the default implementation of this method does nothing);
3.  creates a coroutine by calling `run()`; and
4.  schedules immediate execution of the process.

<div class="callout" markdown="1">

The word "process" can be confusing.
These are *not* operating system processes with their own memory and permissions,
but rather simulated entities.

</div>

<div class="callout" markdown="1">

A process can *only* be interrupted at an `await` point.
Exceptions *cannot* be raised from the outside at arbitrary points.

</div>

## `Timeout`: Waiting Until

A `Timeout` object schedules a callback at a future time.
Processes don't normally create these objects directly;
instead,
a class derived from `Process` can call `self.timeout(duration)`.

## `Queue` and `PriorityQueue`: Exchanging Data

`Queue` enables processes to exchange data.
It has two members:
a list of items being passed between processes,
and a list of processes waiting for items.
The invariant for `Queue` is that one or the other list must be empty,
i.e.,
if there are processes waiting then there aren't any items to take,
while if there are items waiting to be taken there aren't any waiting processes.

`Queue.put(item)` either adds an item to the queue
or passing it to a waiting process.
Conversely,
`Queue.get()` either gets an item immediately
or adds the calling process to the list of waiters.

`PriorityQueue` uses `heapq` operations to maintain ordering,
which means items must be comparable (i.e., must implement `__lt__`).
`get()` pops the minimum element;
`put()` pushes onto the heap and potentially satisfies a waiting getter.

## `Resource`: Capacity-Limited Sharing

The `Resource` class simulates a shared resource with limited capacity.
That capacity is the maximum number of concurrent users.
If the resource `res` is below capacity when `res.acquire()` is called,
it calls increments the internal count and immediately succeeds;
otherwise,
it adds the caller to the list of waiting processes.
Similarly,
`res.release()` decrements the count and then checks the list of waiting processes.
If there are any,
it calls `evt.succeed()` for the event representing the first waiting process.

## `Barrier`: Synchronizing Multiple Processes

A `Barrier` holds multiple processes until they are explicitly released,
i.e.,
it synchronizes multiple processes.

-  `wait()` adds the caller to the list of waiters.
-  `release()` releases all waiting processes and clears the list.

## AllOf: Waiting for Multiple Events

`AllOf` succeeds when all provided events complete.
A process calls `AllOf` like this:

```python
await AllOf(self._env, a=self.timeout(5), b=self.timeout(10))
```

The (eventual) result is a dictionary in which
the name of the events are keys and the results of the events are values;
in this case,
the keys will be `"a"` and `"b"`.
This gives callers an easy way to keep track of events,
though it *doesn't* support waiting on all events in a list.

<div class="callout" markdown="1">

`AllOf`'s interface would be tidier
if it didn't require the simulation environment as its first argument.
However,
removing it made the implementation significantly more complicated.

</div>

## FirstOf: Racing Multiple Events

`FirstOf` succeeds as soon as *any* of the provided events succeeds,
and then cancels all of the other events.
Its interface is similar to `AllOf`'s,
except it returns a `(key, value)` tuple identify the winning event.
