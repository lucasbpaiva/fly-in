from graph import Graph, Zone, Connection
from .drone import Drone


class SimulationEngine:
    """Central state machine resolving the Multi-Agent Pathfinding simulation.

    Manages turn execution, physical drone movements across the graph topology,
    capacity enforcement, and standard output generation.
    """
    def __init__(self, graph: Graph) -> None:
        """Initialize the engine and spawn all drones in the starting zone.

        Args:
            graph: The topological network containing zones and connections.
        """
        self.graph = graph
        self.turn: int = 0
        self.drones: dict[str, Drone] = {}
        for i in range(1, graph.nb_drones + 1):
            drone_id = f"D{i}"
            drone = Drone(drone_id, initial_location=graph.start_zone)
            self.drones[drone_id] = drone
            graph.start_zone.add_drone(drone_id)

    @property
    def active_drones(self) -> list[Drone]:
        """Dynamically filter the registry for drones currently in transit."""
        return [d for d in self.drones.values() if not d.is_finished]

    @property
    def is_finished(self) -> bool:
        """Evaluate if every drone in the simulation has reached end zone."""
        return all(drone.is_finished for drone in self.drones.values())

    def play_turn(self, planned_moves: dict[str, Zone | Connection]) -> str:
        """Execute one simulation turn, making all requested drone movements.

        Args:
            planned_moves: A dictionary mapping drone string IDs to their
                requested target (Zone or Connection).

        Returns:
            A list of formatted strings (e.g. 'D1-hub_a') for successful moves.
        """
        for connection in self.graph.edges:
            connection.turn_usage = 0
        successful_moves = []
        for drone_id, target in planned_moves.items():
            if self.attempt_move(drone_id, target):
                successful_moves.append(f"{drone_id}-{target.name}")
        self.turn += 1
        self.check_completions()
        return " ".join(successful_moves)

    def attempt_move(self, drone_id: str, target: Zone | Connection) -> bool:
        """Process a single drone's movement subject to physical capacities.

        Args:
            drone_id: The string identifier of the moving drone.
            target: The adjacent Zone or Connection to enter.

        Returns:
            True if the move was valid and executed, False if rejected.
        """
        drone = self.drones[drone_id]
        current = drone.location
        # --- SCENARIO A: Target is a Connection (2+ turn transit) ---
        if isinstance(target, Connection):
            if target.is_full:
                return False
            current.remove_drone(drone.id)
            target.add_drone(drone.id)
            drone.location = target
            return True
        # --- SCENARIO B: Target is a Zone (1-turn direct jump) ---
        if isinstance(target, Zone):
            if target.is_full:
                return False
            # If the drone is already in a connection, it's exiting it
            if isinstance(current, Connection):
                current.remove_drone(drone.id)
                target.add_drone(drone.id)
                drone.location = target
                return True
            # If jumping Zone -> Zone, find the connecting edge and lock it
            connection = self.graph.get_connection(current.name, target.name)
            if not connection or connection.is_full:
                return False
            # Reserve the connection for this turn,
            # but move the drone to the zone
            connection.turn_usage += 1
            current.remove_drone(drone.id)
            target.add_drone(drone.id)
            drone.location = target
            return True
        return False

    def check_completions(self) -> None:
        """Evaluate active drones and mark them finished if they arrived."""
        for drone in self.drones.values():
            # Only check drones that are still active
            if not drone.is_finished and drone.location == self.graph.end_zone:
                drone.is_finished = True
