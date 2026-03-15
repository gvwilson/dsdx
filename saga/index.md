# The Saga Pattern

When you book a flight, reserve a hotel, and rent a car in a single transaction,
what happens if the car rental fails but the flight and hotel are already reserved?
In a monolithic system you would roll back the entire transaction,
but in a microservices architecture using separate databases for flights, hotels, and cars,
traditional ACID transactions don't work.

The Saga pattern solves this by breaking long-running transactions into a sequence of local transactions,
each with a [compensating action](g:compensation) to undo its effects if the overall transaction fails.
This enables distributed transactions without distributed locks,
maintaining eventual consistency while handling failures gracefully.

The pattern is a response to the fact that distributed transactions using two-phase commit don't scale.
Sagas trade immediate consistency for availability and fault tolerance,
but as we'll see,
bring constraints of their own.

## The Saga Pattern {: #saga-pattern}

A Saga is a sequence of local transactions,
each of which updates a single service and publishes an event or message to trigger the next transaction.
If a transaction fails,
the Saga executes compensating transactions to undo the changes made by preceding transactions.

Unlike two-phase commit,
which uses prepare/commit phases and locks,
Sagas commit each step immediately and use compensation to handle failures.
The pattern can be implemented in one of two ways.

-   Orchestration:
    a central coordinator tells each service what to do.
    This is easier to understand and monitor,
    but the coordinator is a coordination point.

-   Choreography:
    each service listens for events and decides what to do next.
    Its decentralization makes it more scalable,
    but also makes it harder to understand and monitor.

Whichever approach is used,
each forward step must be define a backward compensation that is retryable and idempotent.
The first requirement is self-explanatory;
the second means that the compensation has the same effect on the system
no matter how many times it is tried.
(A simple example is multiplying a value by 1:
it can be done any number of times, but always has the same result.)

Compensations must be idempotent because it's possible for a workflow to go forward and backward several times.
Compensations can be implemented as negative transitions,
but it is often easier to implement them by saving the state before the transition,
such as the account balance,
and then restoring that state.
These approaches can be mixed together in a single workflow
depending on which is easiest to use with a particular external service.

## Core Data Structures {: #saga-struct}

Let's build a travel booking saga with flights, hotels, and car rentals.
We start by defining the states that the saga as a whole
and the individual transactions
can be in:

<div data-inc="saga_types.py" data-filter="inc=enum"></div>

We then create structures to represent the saga's state  machine.
Each step has a forward transaction and a backward compensation.

<div data-inc="saga_types.py" data-filter="inc=sagatypes"></div>

## Service Implementations {: #saga-services}

We can now implement the three microservices involved in the saga.
Each service manages its own local state
and provides both forward (book) and backward (cancel) operations.
The flight service manages seat availability;
we have given it a 10% random failure rate to simulate real-world unreliability:

<div data-inc="booking_services.py" data-filter="inc=flight_service"></div>

The hotel service follows the same pattern with a 15% failure rate and room inventory:

<div data-inc="booking_services.py" data-filter="inc=hotel_service"></div>

Finally,
the car rental service has a 30% failure rate to demonstrate more frequent compensation:

<div data-inc="booking_services.py" data-filter="inc=car_service"></div>

Each service is autonomous:
it manages its own database and can succeed or fail independently.

## Orchestration-Based Saga {: #saga-orch}

The orchestrator coordinates the sequence of transactions.
It stores references to each service and processes requests from a queue:

<div data-inc="saga_orchestrator.py" data-filter="inc=orch_init"></div>

When a booking request arrives,
`execute_saga` builds the list of steps and drives them forward,
triggering compensation if any step fails:

<div data-inc="saga_orchestrator.py" data-filter="inc=orch_execute"></div>

The forward pass runs each step in sequence,
stopping immediately on the first failure:

<div data-inc="saga_orchestrator.py" data-filter="inc=orch_forward"></div>

The compensation pass runs in reverse,
undoing each completed step:

<div data-inc="saga_orchestrator.py" data-filter="inc=orch_compensate"></div>

## Basic Orchestration Example

Let's see orchestration in action:

<div data-inc="ex_saga.py" data-filter="inc=orchestratedexample"></div>
<div data-inc="ex_saga.txt"></div>
