# Saga Pattern for Distributed Transactions

Implementation of the Saga pattern for managing long-running distributed transactions
across microservices without distributed locks.

## Overview

The Saga pattern breaks distributed transactions into a sequence of local transactions,
each with a compensating action to undo its effects if the overall transaction fails.
This enables eventual consistency without the scalability limitations of two-phase commit (2PC).

## Files

### Core Components

- `saga_types.py` - Data structures (SagaStep, SagaExecution, BookingRequest, events)
- `booking_services.py` - Microservices (FlightService, HotelService, CarRentalService)
- `saga_orchestrator.py` - Centralized saga coordinator

### Examples

- `example_orchestrated_saga.py` - Travel booking with compensation on failure

## Key Concepts

### Saga Components

1. **Local Transactions**: Each service performs its own database transaction
2. **Compensating Transactions**: Reverse the effects of completed transactions
3. **Saga Coordinator**: Orchestrates the sequence (in orchestration pattern)
4. **Events**: Trigger next steps (in choreography pattern)

### Forward and Backward Recovery

**Forward Recovery** (execute next step):
- Book flight → Book hotel → Book car

**Backward Recovery** (compensation):
- Cancel car → Cancel hotel → Cancel flight

### Compensating Transactions

Compensations are NOT rollbacks—they're new transactions that semantically undo:

```python
# Forward transaction
def book_flight(booking_id):
    seats_available -= 1
    bookings[booking_id] = {"status": "booked"}

# Compensation (not a rollback!)
def cancel_flight(booking_id):
    seats_available += 1
    bookings[booking_id]["status"] = "canceled"
```

Key properties:
- **Idempotent**: Can be retried safely
- **Retryable**: Will eventually succeed
- **Semantic**: Business-level undo, not technical rollback

### Orchestration vs Choreography

**Orchestration** (implemented here):
- Central coordinator directs all steps
- Easy to understand and monitor
- Clear workflow visibility
- Coordinator is coordination point

**Choreography**:
- Services listen to events and react
- No central coordinator
- More loosely coupled
- Harder to monitor overall progress

## Running the Example

### Basic Travel Booking

```bash
python example_orchestrated_saga.py
```

Shows:
- 5 booking attempts
- Some bookings succeed (all 3 services available)
- Some fail (car rental often unavailable)
- Failed bookings trigger compensation
- Resources released when bookings fail

## Architecture

```
SagaOrchestrator
      |
      +-- Execute Forward
      |       |
      |       +-- Step 1: Book Flight (FlightService)
      |       |       ✓ Success → Continue
      |       |
      |       +-- Step 2: Book Hotel (HotelService)
      |       |       ✓ Success → Continue
      |       |
      |       +-- Step 3: Book Car (CarRentalService)
      |               ✗ FAILED → Start compensation
      |
      +-- Execute Compensation (reverse order)
              |
              +-- Compensate: Cancel Hotel
              |       ✓ Resources released
              |
              +-- Compensate: Cancel Flight
                      ✓ Resources released
```

## Saga Execution Flow

### Successful Saga

```
1. Orchestrator: Execute book_flight
   FlightService: ✓ Flight booked
   
2. Orchestrator: Execute book_hotel
   HotelService: ✓ Hotel booked
   
3. Orchestrator: Execute book_car
   CarRentalService: ✓ Car booked
   
Result: ✓✓✓ Saga COMPLETED ✓✓✓
```

### Failed Saga with Compensation

```
1. Orchestrator: Execute book_flight
   FlightService: ✓ Flight booked
   
2. Orchestrator: Execute book_hotel
   HotelService: ✓ Hotel booked
   
3. Orchestrator: Execute book_car
   CarRentalService: ✗ Booking FAILED - no cars
   
4. Orchestrator: Starting compensation...
   
5. Orchestrator: Compensating book_hotel
   HotelService: ✓ Hotel canceled
   
6. Orchestrator: Compensating book_flight
   FlightService: ✓ Flight canceled
   
Result: ✗✗✗ Saga FAILED - compensated ✗✗✗
```

## Design Patterns

### Pivot Transaction

The last step that cannot be compensated:

```python
steps = [
    compensatable_step_1,  # Can undo
    compensatable_step_2,  # Can undo
    pivot_transaction      # Cannot undo (e.g., send notification)
]
```

Place risky operations early and irreversible operations last.

### Semantic Locking

Prevent dirty reads during saga execution:

```python
# Mark booking as pending
booking["status"] = "pending"

# Execute saga
saga.execute()

# Update to final status
if saga.success:
    booking["status"] = "confirmed"
else:
    booking["status"] = "failed"
```

### Timeout Management

```python
# Set timeout for each step
step.timeout = 30  # seconds

# Compensate on timeout
if elapsed > step.timeout:
    execute_compensation()
```

## Real-World Applications

### E-Commerce Order

1. Reserve inventory
2. Charge payment
3. Create shipment
4. Send confirmation email (pivot - cannot undo)

Compensation: Cancel shipment, refund payment, release inventory

### Banking Transfer

1. Debit source account
2. Credit destination account
3. Record transaction
4. Send notifications

Compensation: Credit source account, debit destination account

### Video Processing

1. Upload video
2. Transcode formats
3. Generate thumbnails
4. Update metadata
5. Publish to CDN (pivot)

Compensation: Delete transcoded files, remove metadata

## Saga vs 2PC Comparison

| Feature | Saga | Two-Phase Commit |
|---------|------|------------------|
| Locks | No locks | Locks resources |
| Isolation | Not isolated | Full isolation |
| Consistency | Eventual | Immediate |
| Availability | High | Lower |
| Coordinator failure | Recoverable | Blocks entire system |
| Cross-organization | Works | Impractical |
| Scalability | Excellent | Poor |
| Complexity | Compensations | Prepare/commit protocol |

## Production Considerations

### Idempotency

Ensure operations can be retried:

```python
# Bad: Not idempotent
balance = balance - amount

# Good: Idempotent with check
if not already_processed(transaction_id):
    balance = balance - amount
    mark_processed(transaction_id)
```

### Compensation Failures

What if compensation fails?

- Retry with exponential backoff
- Dead letter queue for manual intervention
- Alert operations team
- Implement circuit breakers

### Monitoring

Track:
- Saga completion rate
- Compensation frequency
- Step failure rates
- Duration of each step
- Pending saga count

### Testing

Test scenarios:
- All steps succeed
- Each step fails
- Compensation failures
- Timeouts
- Concurrent sagas

## Limitations

Sagas provide eventual consistency, not ACID:

- **Dirty Reads**: Other transactions see intermediate state
- **Lost Updates**: Concurrent sagas may conflict
- **Non-repeatable Reads**: State may change between reads

Solutions:
- Semantic locks
- Optimistic locking
- Versioning
- Accept eventual consistency

## Further Reading

- [Sagas (Original Paper)](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf)
- [Microservices Patterns: Sagas](https://microservices.io/patterns/data/saga.html)
- [Azure: Saga Pattern](https://docs.microsoft.com/en-us/azure/architecture/reference-architectures/saga/saga)
- [AWS: Saga Pattern with Step Functions](https://aws.amazon.com/blogs/compute/implementing-the-saga-pattern-with-aws-step-functions/)
