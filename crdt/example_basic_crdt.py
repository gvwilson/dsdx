"""Basic CRDT convergence demonstration."""

from asimpy import Environment
from crdt_replica import CRDTReplica
from crdt_workload import CRDTWorkload


def run_basic_simulation():
    """Demonstrate basic CRDT convergence."""
    env = Environment()
    
    # Create three replicas
    replica1 = CRDTReplica(env, "R1", sync_interval=3.0)
    replica2 = CRDTReplica(env, "R2", sync_interval=3.0)
    replica3 = CRDTReplica(env, "R3", sync_interval=3.0)
    
    # Connect replicas in a mesh
    replica1.add_peer(replica2)
    replica1.add_peer(replica3)
    replica2.add_peer(replica1)
    replica2.add_peer(replica3)
    replica3.add_peer(replica1)
    replica3.add_peer(replica2)
    
    # Replica 1: increment counter
    CRDTWorkload(env, replica1, [
        ("increment", 5),
        ("set", "Alice"),
        ("add", "apple"),
        ("add", "banana"),
    ])
    
    # Replica 2: concurrent operations
    CRDTWorkload(env, replica2, [
        ("increment", 3),
        ("set", "Bob"),
        ("add", "cherry"),
    ])
    
    # Replica 3: more concurrent operations
    CRDTWorkload(env, replica3, [
        ("decrement", 2),
        ("set", "Charlie"),
        ("add", "banana"),  # Concurrent add of same element
        ("remove", "apple"),  # Concurrent remove
    ])
    
    # Run simulation
    env.run(until=15)
    
    # Check convergence
    print("\n=== Final States ===")
    print(f"R1: Counter={replica1.counter.value()}, "
          f"Register='{replica1.register.value}', "
          f"Set={replica1.orset.value()}")
    print(f"R2: Counter={replica2.counter.value()}, "
          f"Register='{replica2.register.value}', "
          f"Set={replica2.orset.value()}")
    print(f"R3: Counter={replica3.counter.value()}, "
          f"Register='{replica3.register.value}', "
          f"Set={replica3.orset.value()}")
    
    # Verify convergence
    assert replica1.counter.value() == replica2.counter.value() == replica3.counter.value()
    assert replica1.register.value == replica2.register.value == replica3.register.value
    assert replica1.orset.value() == replica2.orset.value() == replica3.orset.value()
    
    print("All replicas converged!")


if __name__ == "__main__":
    run_basic_simulation()
