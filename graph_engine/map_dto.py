from .zone import Zone
from .connection import Connection
from dataclasses import dataclass


@dataclass
class Map:
    """Data Transfer Object representing a fully validated simulation map.

    Acts as a static snapshot of the parsed environment topology, providing
    the necessary entities to construct the pathfinding graph.

    Attributes:
        nb_drones: Total number of drones participating in the simulation.
        start_zone: The designated origin zone where all drones begin.
        end_zone: The designated destination zone for all drones.
        zones: A dictionary mapping unique zone names to their Zone instances.
        connections: A list of all validated bidirectional transit links.
    """
    nb_drones: int
    start_zone: Zone
    end_zone: Zone
    zones: dict[str, Zone]
    connections: list[Connection]
