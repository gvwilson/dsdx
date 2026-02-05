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

```python
from asimpy import Environment, Process, Queue
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import random


class SagaStatus(Enum):
    """Status of a saga execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"


class TransactionStatus(Enum):
    """Status of individual transaction."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"


@dataclass
class SagaStep:
    """A step in the saga with transaction and compensation."""
    name: str
    service_name: str
    transaction: Callable[..., bool]  # Returns True if successful
    compensation: Optional[Callable[..., bool]]  # Returns True if successful
    
    def __str__(self) -> str:
        return f"Step({self.name})"


@dataclass
class SagaExecution:
    """Tracks execution of a saga instance."""
    saga_id: str
    steps: List[SagaStep]
    status: SagaStatus = SagaStatus.PENDING
    current_step: int = 0
    completed_steps: List[str] = field(default_factory=list)
    failed_step: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"Saga({self.saga_id}, {self.status.value}, step {self.current_step}/{len(self.steps)})"


@dataclass
class BookingRequest:
    """Travel booking request."""
    booking_id: str
    customer_id: str
    flight_id: str
    hotel_id: str
    car_id: str
    
    def __str__(self) -> str:
        return f"Booking({self.booking_id})"


@dataclass
class SagaEvent:
    """Event in choreographed saga."""
    event_type: str  # "flight_booked", "flight_failed", etc.
    saga_id: str
    data: Dict[str, Any]
    
    def __str__(self) -> str:
        return f"Event({self.event_type})"
```

These structures represent the Saga's state machine.
Each step has a forward transaction and a backward compensation.

## Service Implementations

Let's implement the microservices that participate in the Saga.
Each service manages its own local state and provides both forward (book) and backward (cancel) operations:

```python
class FlightService(Process):
    """Microservice for booking flights."""
    
    def init(self) -> None:
        self.bookings: Dict[str, Dict[str, Any]] = {}
        self.request_queue: Queue = Queue(self._env)
        self.available_seats = 10
        
        print(f"[{self.now:.1f}] FlightService started (seats: {self.available_seats})")
    
    async def run(self) -> None:
        """Handle flight booking requests."""
        while True:
            await self.timeout(1.0)
    
    def book_flight(self, booking_id: str, flight_id: str) -> bool:
        """Book a flight (forward transaction)."""
        print(f"[{self.now:.1f}] FlightService: Booking flight {flight_id}")
        
        # Simulate occasional failures
        if random.random() < 0.1:
            print(f"[{self.now:.1f}] FlightService: Booking FAILED - system error")
            return False
        
        if self.available_seats <= 0:
            print(f"[{self.now:.1f}] FlightService: Booking FAILED - no seats")
            return False
        
        self.available_seats -= 1
        self.bookings[booking_id] = {
            "flight_id": flight_id,
            "status": "booked",
            "seats": 1
        }
        
        print(f"[{self.now:.1f}] FlightService: ✓ Flight booked "
              f"(remaining: {self.available_seats})")
        return True
    
    def cancel_flight(self, booking_id: str) -> bool:
        """Cancel flight booking (compensation)."""
        print(f"[{self.now:.1f}] FlightService: COMPENSATING - "
              f"canceling {booking_id}")
        
        if booking_id not in self.bookings:
            print(f"[{self.now:.1f}] FlightService: No booking to cancel")
            return True
        
        seats = self.bookings[booking_id].get("seats", 1)
        self.available_seats += seats
        self.bookings[booking_id]["status"] = "canceled"
        
        print(f"[{self.now:.1f}] FlightService: ✓ Flight canceled "
              f"(available: {self.available_seats})")
        return True


class HotelService(Process):
    """Microservice for booking hotels."""
    
    def init(self) -> None:
        self.bookings: Dict[str, Dict[str, Any]] = {}
        self.request_queue: Queue = Queue(self._env)
        self.available_rooms = 5
        
        print(f"[{self.now:.1f}] HotelService started (rooms: {self.available_rooms})")
    
    async def run(self) -> None:
        """Handle hotel booking requests."""
        while True:
            await self.timeout(1.0)
    
    def book_hotel(self, booking_id: str, hotel_id: str) -> bool:
        """Book a hotel (forward transaction)."""
        print(f"[{self.now:.1f}] HotelService: Booking hotel {hotel_id}")
        
        # Simulate occasional failures  
        if random.random() < 0.15:
            print(f"[{self.now:.1f}] HotelService: Booking FAILED - no rooms")
            return False
        
        if self.available_rooms <= 0:
            print(f"[{self.now:.1f}] HotelService: Booking FAILED - no rooms")
            return False
        
        self.available_rooms -= 1
        self.bookings[booking_id] = {
            "hotel_id": hotel_id,
            "status": "booked",
            "rooms": 1
        }
        
        print(f"[{self.now:.1f}] HotelService: ✓ Hotel booked "
              f"(remaining: {self.available_rooms})")
        return True
    
    def cancel_hotel(self, booking_id: str) -> bool:
        """Cancel hotel booking (compensation)."""
        print(f"[{self.now:.1f}] HotelService: COMPENSATING - "
              f"canceling {booking_id}")
        
        if booking_id not in self.bookings:
            print(f"[{self.now:.1f}] HotelService: No booking to cancel")
            return True
        
        rooms = self.bookings[booking_id].get("rooms", 1)
        self.available_rooms += rooms
        self.bookings[booking_id]["status"] = "canceled"
        
        print(f"[{self.now:.1f}] HotelService: ✓ Hotel canceled "
              f"(available: {self.available_rooms})")
        return True


class CarRentalService(Process):
    """Microservice for renting cars."""
    
    def init(self) -> None:
        self.bookings: Dict[str, Dict[str, Any]] = {}
        self.request_queue: Queue = Queue(self._env)
        self.available_cars = 3
        
        print(f"[{self.now:.1f}] CarRentalService started (cars: {self.available_cars})")
    
    async def run(self) -> None:
        """Handle car rental requests."""
        while True:
            await self.timeout(1.0)
    
    def book_car(self, booking_id: str, car_id: str) -> bool:
        """Book a car (forward transaction)."""
        print(f"[{self.now:.1f}] CarRentalService: Booking car {car_id}")
        
        # Simulate higher failure rate for demonstration
        if random.random() < 0.3:
            print(f"[{self.now:.1f}] CarRentalService: Booking FAILED - no cars")
            return False
        
        if self.available_cars <= 0:
            print(f"[{self.now:.1f}] CarRentalService: Booking FAILED - no cars")
            return False
        
        self.available_cars -= 1
        self.bookings[booking_id] = {
            "car_id": car_id,
            "status": "booked",
            "cars": 1
        }
        
        print(f"[{self.now:.1f}] CarRentalService: ✓ Car booked "
              f"(remaining: {self.available_cars})")
        return True
    
    def cancel_car(self, booking_id: str) -> bool:
        """Cancel car rental (compensation)."""
        print(f"[{self.now:.1f}] CarRentalService: COMPENSATING - "
              f"canceling {booking_id}")
        
        if booking_id not in self.bookings:
            print(f"[{self.now:.1f}] CarRentalService: No booking to cancel")
            return True
        
        cars = self.bookings[booking_id].get("cars", 1)
        self.available_cars += cars
        self.bookings[booking_id]["status"] = "canceled"
        
        print(f"[{self.now:.1f}] CarRentalService: ✓ Car canceled "
              f"(available: {self.available_cars})")
        return True
```

Each service is autonomous—it manages its own database and can succeed or fail independently.

## Orchestration-Based Saga

The orchestrator coordinates the sequence of transactions.
It executes steps sequentially and handles compensation if any step fails:

```python
class SagaOrchestrator(Process):
    """Centralized saga coordinator (orchestration pattern)."""
    
    def init(self, flight_service: FlightService,
             hotel_service: HotelService,
             car_service: CarRentalService) -> None:
        self.flight_service = flight_service
        self.hotel_service = hotel_service
        self.car_service = car_service
        
        self.request_queue: Queue = Queue(self._env)
        self.active_sagas: Dict[str, SagaExecution] = {}
        
        # Statistics
        self.sagas_completed = 0
        self.sagas_failed = 0
        
        print(f"[{self.now:.1f}] SagaOrchestrator started\n")
    
    async def run(self) -> None:
        """Process booking requests."""
        while True:
            request = await self.request_queue.get()
            await self.execute_saga(request)
    
    async def execute_saga(self, booking: BookingRequest) -> None:
        """Execute travel booking saga."""
        print(f"[{self.now:.1f}] {'='*60}")
        print(f"[{self.now:.1f}] Starting saga for {booking}")
        print(f"[{self.now:.1f}] {'='*60}")
        
        # Define saga steps
        steps = [
            SagaStep(
                name="book_flight",
                service_name="FlightService",
                transaction=lambda: self.flight_service.book_flight(
                    booking.booking_id, booking.flight_id
                ),
                compensation=lambda: self.flight_service.cancel_flight(
                    booking.booking_id
                )
            ),
            SagaStep(
                name="book_hotel",
                service_name="HotelService",
                transaction=lambda: self.hotel_service.book_hotel(
                    booking.booking_id, booking.hotel_id
                ),
                compensation=lambda: self.hotel_service.cancel_hotel(
                    booking.booking_id
                )
            ),
            SagaStep(
                name="book_car",
                service_name="CarRentalService",
                transaction=lambda: self.car_service.book_car(
                    booking.booking_id, booking.car_id
                ),
                compensation=None  # Last step doesn't need compensation
            )
        ]
        
        saga = SagaExecution(
            saga_id=booking.booking_id,
            steps=steps,
            status=SagaStatus.IN_PROGRESS
        )
        
        self.active_sagas[booking.booking_id] = saga
        
        # Execute forward transactions
        success = await self.execute_forward(saga)
        
        if success:
            saga.status = SagaStatus.COMPLETED
            self.sagas_completed += 1
            print(f"\n[{self.now:.1f}] ✓✓✓ Saga {saga.saga_id} COMPLETED ✓✓✓\n")
        else:
            # Execute compensations
            saga.status = SagaStatus.COMPENSATING
            await self.execute_compensation(saga)
            saga.status = SagaStatus.FAILED
            self.sagas_failed += 1
            print(f"\n[{self.now:.1f}] ✗✗✗ Saga {saga.saga_id} FAILED - "
                  f"compensated ✗✗✗\n")
    
    async def execute_forward(self, saga: SagaExecution) -> bool:
        """Execute forward transactions in sequence."""
        for i, step in enumerate(saga.steps):
            saga.current_step = i
            
            print(f"[{self.now:.1f}] Orchestrator: Executing step {i+1}/"
                  f"{len(saga.steps)}: {step.name}")
            
            # Simulate network delay
            await self.timeout(0.3)
            
            # Execute transaction
            success = step.transaction()
            
            if success:
                saga.completed_steps.append(step.name)
            else:
                saga.failed_step = step.name
                print(f"[{self.now:.1f}] Orchestrator: Step {step.name} FAILED")
                return False
        
        return True
    
    async def execute_compensation(self, saga: SagaExecution) -> None:
        """Execute compensating transactions in reverse order."""
        print(f"\n[{self.now:.1f}] Orchestrator: Starting compensation...")
        
        # Compensate in reverse order
        for step_name in reversed(saga.completed_steps):
            # Find the step
            step = next(s for s in saga.steps if s.name == step_name)
            
            if step.compensation:
                print(f"[{self.now:.1f}] Orchestrator: Compensating {step_name}")
                
                # Simulate network delay
                await self.timeout(0.2)
                
                success = step.compensation()
                
                if not success:
                    print(f"[{self.now:.1f}] Orchestrator: WARNING - "
                          f"Compensation {step_name} failed! Manual intervention needed.")
```

The orchestrator provides a clear, centralized view of the workflow.
It's easy to monitor and debug.

## Basic Orchestration Example

Let's see orchestration in action:

```python
def run_orchestrated_saga() -> None:
    """Demonstrate orchestration-based saga."""
    env = Environment()
    
    # Create services
    flight_service = FlightService(env)
    hotel_service = HotelService(env)
    car_service = CarRentalService(env)
    
    # Create orchestrator
    orchestrator = SagaOrchestrator(
        env, flight_service, hotel_service, car_service
    )
    
    # Submit booking requests
    class BookingGenerator(Process):
        def init(self, orch: SagaOrchestrator) -> None:
            self.orch = orch
        
        async def run(self) -> None:
            for i in range(5):
                booking = BookingRequest(
                    booking_id=f"BOOK{i+1:03d}",
                    customer_id=f"CUST{i+1}",
                    flight_id="FL123",
                    hotel_id="HTL456",
                    car_id="CAR789"
                )
                
                await self.orch.request_queue.put(booking)
                await self.timeout(3.0)
    
    BookingGenerator(env, orchestrator)
    
    # Run simulation
    env.run(until=40)
    
    # Print summary
    print("\n" + "="*60)
    print("Final State:")
    print("="*60)
    print(f"Flight seats available: {flight_service.available_seats}/10")
    print(f"Hotel rooms available: {hotel_service.available_rooms}/5")
    print(f"Cars available: {car_service.available_cars}/3")
    print(f"\nCompleted sagas: {orchestrator.sagas_completed}")
    print(f"Failed sagas: {orchestrator.sagas_failed}")


if __name__ == "__main__":
    run_orchestrated_saga()
```

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
