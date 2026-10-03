from graph import Graph, Zone
from .drone import Drone


class SimulationEngine:
    """Class SimulationEngine."""
    def __init__(self, graph: Graph) -> None:
        """Constructor method."""
        self.turn: int = 0
        self.is_finished: bool = False
        self.active_drones: list[Drone] = []
        self.drone_locations: dict[str, Zone] = {}
        for i in range(1, graph.nb_drones + 1):
            drone = Drone(f"D{i}")
            self.active_drones.append(drone)
            self.drone_locations[drone.id] = graph.start_zone
            graph.start_zone.occupants.add(drone.id)
