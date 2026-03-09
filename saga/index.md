# The Saga Pattern

When you book a flight, reserve a hotel, and rent a car in a single transaction, what happens if the car rental fails but the flight and hotel are already reserved? In a monolithic database, you'd roll back the entire transaction.
But in a microservices architecture with separate databases for flights, hotels, and cars, traditional ACID transactions don't work.
The Saga pattern solves this by breaking long-running transactions into a sequence of local transactions, each with a compensating action to undo its effects if the overall transaction fails.

Netflix uses Sagas to coordinate video encoding pipelines across multiple services.
E-commerce platforms use them for order processing—reserving inventory, charging payment, arranging shipping.
Travel booking systems use them to coordinate flights, hotels, and rental cars.
The Saga pattern enables distributed transactions without distributed locks, maintaining eventual consistency while handling failures gracefully.

This pattern emerged from a fundamental limitation: distributed transactions using two-phase commit (2PC) don't scale.
They require holding locks across services, creating bottlenecks and failure points.
Sagas trade immediate consistency for availability and fault tolerance—a deliberate choice that fits modern distributed systems.

## The Saga Pattern

A Saga is a sequence of local transactions where each transaction updates a single service and publishes an event or message to trigger the next transaction.
If a transaction fails, the Saga executes compensating transactions to undo the changes made by preceding transactions.

The pattern has two main approaches:

**Orchestration**: A central coordinator tells each service what to do.
Easier to understand and monitor, but the coordinator is a coordination point.

**Choreography**: Each service listens for events and decides what to do next.
Decentralized, no single point of coordination, but harder to understand and monitor.

The key components are:

1.  **Local transactions**: Each service performs its own transaction
1.  **Compensating transactions**: Reverse the effects of local transactions  
1.  **Saga coordinator** (orchestration): Manages the sequence
1.  **Events** (choreography): Trigger next steps in the sequence

Unlike 2PC which uses prepare/commit phases and locks, Sagas commit each step immediately and use compensation to handle failures.

## Core Data Structures

Let's build a travel booking Saga with flights, hotels, and car rentals:

<div data-inc="saga_types.py" data-filter="inc=sagatypes"></div>

These structures represent the Saga's state machine.
Each step has a forward transaction and a backward compensation.

## Service Implementations

Let's implement the microservices that participate in the Saga.
Each service manages its own local state and provides both forward (book) and backward (cancel) operations.

The flight service manages seat availability and implements a 10% random failure rate to simulate real-world unreliability:

<div data-inc="booking_services.py" data-filter="inc=flight_service"></div>

The hotel service follows the same pattern with a 15% failure rate and room inventory:

<div data-inc="booking_services.py" data-filter="inc=hotel_service"></div>

The car rental service has a 30% failure rate to demonstrate more frequent compensation:

<div data-inc="booking_services.py" data-filter="inc=car_service"></div>

Each service is autonomous—it manages its own database and can succeed or fail independently.

## Orchestration-Based Saga

The orchestrator coordinates the sequence of transactions.
It stores references to each service and processes requests from a queue:

<div data-inc="saga_orchestrator.py" data-filter="inc=orch_init"></div>

When a booking request arrives, `execute_saga` builds the list of steps and drives them forward, triggering compensation if any step fails:

<div data-inc="saga_orchestrator.py" data-filter="inc=orch_execute"></div>

The forward pass runs each step in sequence, stopping immediately on the first failure:

<div data-inc="saga_orchestrator.py" data-filter="inc=orch_forward"></div>

The compensation pass runs in reverse, undoing each completed step:

<div data-inc="saga_orchestrator.py" data-filter="inc=orch_compensate"></div>

The orchestrator provides a clear, centralized view of the workflow.
It's easy to monitor and debug.

## Basic Orchestration Example

Let's see orchestration in action:

<div data-inc="example_orchestrated_saga.py" data-filter="inc=orchestratedexample"></div>

This demonstrates how compensation restores system state when bookings fail partway through.

## Key Saga Concepts

### Compensating Transactions

Compensations are NOT rollbacks—they're forward operations that semantically undo effects:

- **Cancel reservation** (not "delete booking record")
- **Refund payment** (not "undo charge")
- **Return inventory** (not "remove allocation")

Compensations must be:
- **Idempotent**: Can be retried safely
- **Retryable**: Will eventually succeed  
- **Commutative**: Order doesn't matter (where possible)

### Semantic Locking

Prevent dirty reads during saga execution:

- Mark records as "pending"
- Users see "Processing..." status
- Don't show incomplete state
- Use optimistic locking for conflicts

### Pivot Transaction

The last transaction in a Saga that can't be compensated.
For example:
- Sending email notification
- Shipping physical goods
- Executing wire transfer

Design Sagas so risky operations happen early (compensatable) and irreversible operations happen last.

## Trade-offs: Orchestration vs Choreography

**Orchestration Advantages**:
- Easy to understand and debug
- Centralized monitoring
- Clear workflow visualization
- Simpler testing
- Easy to add/modify steps

**Orchestration Disadvantages**:
- Coordinator is coordination point
- Coordinator becomes complex for large sagas
- Services coupled to orchestrator

**Choreography Advantages**:
- No central coordinator
- Services more loosely coupled
- Better for event-driven architectures
- Scales better
- Natural for domain events

**Choreography Disadvantages**:
- Hard to understand overall flow
- Difficult to monitor
- Debugging is challenging
- Circular dependencies possible
- No single source of truth for saga state

## Saga vs Two-Phase Commit

|  | Saga | 2PC |
|--|------|-----|
| Locks | No locks | Locks resources |
| Isolation | Not isolated | Full isolation |
| Consistency | Eventual | Immediate |
| Availability | High | Lower |
| Coordinator failure | Can recover | Blocks system |
| Cross-org | Works | Impractical |
| Complexity | Compensations | Prepare/commit |

Sagas are preferred for microservices because they don't require locks and work across organizational boundaries.

## Conclusion

The Saga pattern enables distributed transactions through eventual consistency.
The key principles are:

1.  **Local transactions**: Each service commits independently
1.  **Compensations**: Semantic undo operations
1.  **No distributed locks**: Services don't block each other
1.  **Eventual consistency**: State converges over time
1.  **Graceful degradation**: Failures trigger compensations

Sagas trade immediate consistency for availability and scalability.
They work best when:

-   Traditional 2PC is impractical
-   Services have separate databases
-   Long-running transactions span services
-   Eventual consistency is acceptable
-   Operations are compensatable
