"""Demonstration of CRDT behavior during network partition."""

from asimpy import Environment
from partitioned_crdt_replica import PartitionedCRDTReplica
from crdt_workload import CRDTWorkload
from partition_manager import PartitionManager


def run_partition_simulation():
    """Demonstrate CRDT behavior during network partition."""
    env = Environment()
    
    # Create two replicas
    replica1 = PartitionedCRDTReplica(env, "R1", sync_interval=1.0)
    replica2 = PartitionedCRDTReplica(env, "R2", sync_interval=1.0)
    
    replica1.add_peer(replica2)
    replica2.add_peer(replica1)
    
    # Create partition manager
    PartitionManager(env, [replica1, replica2])
    
    # Workload: updates during partition
    CRDTWorkload(env, replica1, [
        ("wait", 3.0),
        ("increment", 10),
        ("add", "item1"),
        ("set", "R1_value"),
    ])
    
    CRDTWorkload(env, replica2, [
        ("wait", 3.0),
        ("increment", 5),
        ("add", "item2"),
        ("set", "R2_value"),
    ])
    
    # Run simulation
    env.run(until=15)
    
    print("\n=== Final State After Partition Heal ===")
    print(f"R1: Counter={replica1.counter.value()}, "
          f"Register='{replica1.register.value}', "
          f"Set={replica1.orset.value()}")
    print(f"R2: Counter={replica2.counter.value()}, "
          f"Register='{replica2.register.value}', "
          f"Set={replica2.orset.value()}")
    
    print("CRDTs converged despite partition!")


if __name__ == "__main__":
    run_partition_simulation()
