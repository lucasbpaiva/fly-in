from .zone import Zone
from .map_dto import Map
from .connection import Connection


class Graph:
    """Operational network topology for the Multi-Agent Pathfinding simulation.

    Converts the static Map DTO into a traversable graph structure, managing
    the bidirectional adjacency list and providing stateful access to all
    simulation nodes.
    """
    def __init__(self, parsed_map: Map) -> None:
        """Initialize the Graph topology from a validated Map object.

        Args:
            parsed_map: The static data transfer object containing the
                validated zones and connections from the parser.
        """
        self.nb_drones: int = parsed_map.nb_drones
        self.start_zone: Zone = parsed_map.start_zone
        self.end_zone: Zone = parsed_map.end_zone
        self.zones: dict[str, Zone] = parsed_map.zones
        self.edges: list[Connection] = parsed_map.connections
        self.adj_list: dict[str, set[Zone]] = self._build_adj_list(self.edges)

    def _build_adj_list(self, edges: list[Connection]) -> dict[str, set[Zone]]:
        """Construct bidirectional adjacency mapping for O(1) neighbor lookups.

        Args:
            edges: The list of validated connection objects.

        Returns:
            A dictionary mapping each zone's string name to a set of directly
            connected Zone objects.
        """
        adj: dict[str, set[Zone]] = {name: set() for name in self.zones}
        for edge in edges:
            adj[edge.zone1].add(self.zones[edge.zone2])
            adj[edge.zone2].add(self.zones[edge.zone1])
        return adj

    def get_neighbors(self, zone_name: str) -> set[Zone]:
        """Retrieve all zones immediately adjacent to the specified zone.

        Args:
            zone_name: The string identifier of the target zone.

        Returns:
            A set of adjacent Zone objects, or an empty set if the zone
            does not exist or has no connections.
        """
        return self.adj_list.get(zone_name, set())
