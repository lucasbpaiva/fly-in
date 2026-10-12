import math
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
        self.connections: dict[tuple[str, str], Connection] = {
            (conn.zone1, conn.zone2): conn for conn in self.edges
        }
        self.adj_list: dict[str, set[Zone]] = self._build_adj_list(self.edges)
        self.max_edge_length = self._calculate_max_edge_length()
        if self.start_zone.type.lower() == "blocked":
            raise ValueError(
                "Invalid graph: "
                f"Start zone '{self.start_zone.name}' cannot be blocked."
            )
        if self.end_zone.type.lower() == "blocked":
            raise ValueError(
                "Invalid graph: "
                f"End zone '{self.end_zone.name}' cannot be blocked."
            )
        self._validate_connectivity()

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

    def _validate_connectivity(self) -> None:
        """Performs BFS to ensure the end zone is reachable from the start."""
        visited = set()
        queue = [self.start_zone.name]
        visited.add(self.start_zone.name)
        while queue:
            current_name = queue.pop(0)
            if current_name == self.end_zone.name:
                return
            for neighbor in self.adj_list.get(current_name, set()):
                is_blocked = neighbor.type.lower() == "blocked"
                if not is_blocked and neighbor.name not in visited:
                    visited.add(neighbor.name)
                    queue.append(neighbor.name)
        raise ValueError(
            "Unsolvable map: No valid path exists from "
            f"'{self.start_zone.name}' to '{self.end_zone.name}' "
            "due to blocked zones or disconnected paths."
        )

    def get_neighbors(
        self, node: Zone | Connection
    ) -> list[Zone | Connection]:
        """Retrieve all nodes immediately adjacent to the specified zone.

        Args:
            node: The Zone or Connection from which we want the neighbors.

        Returns:
            A list of adjacent Zone/Connection, or an empty list if the zone
            does not exist or has no connections.
        """
        neighbors: list[Zone | Connection] = []
        if isinstance(node, Connection):
            neighbors.append(self.zones[node.zone1])
            neighbors.append(self.zones[node.zone2])
            return neighbors
        for adj_zone in self.adj_list.get(node.name, set()):
            zone_type = getattr(adj_zone, "type", "normal").lower()
            if zone_type == "blocked":
                continue
            # If targeting a restricted zone, it's a multi-turn transit.
            # A* must step into the physical Connection object first.
            if zone_type == "restricted":
                conn = self.get_connection(node.name, adj_zone.name)
                if not conn:
                    continue
                neighbors.append(conn)
            else:
                # If priority or normal, it's a 1-turn jump to the Zone.
                neighbors.append(adj_zone)
        return neighbors

    def get_connection(self, zone1: str, zone2: str) -> Connection | None:
        """Retrieve the Connection object linking two zones."""
        return (
            self.connections.get((zone1, zone2))
            or self.connections.get((zone2, zone1))
        )

    def get_coords(self, node: Zone | Connection) -> tuple[float, float]:
        """Extract spatial coordinates safely for Zones and Connections."""
        if isinstance(node, Zone):
            return node.x, -node.y
        # If the drone is inside a connection, approximate its location
        # as the exact midpoint between the two connecting zones.
        z1 = self.zones[node.zone1]
        z2 = self.zones[node.zone2]
        return (z1.x + z2.x) / 2.0, (z1.y + z2.y) / 2.0

    def _calculate_max_edge_length(self) -> float:
        """Find the longest 1-turn jump to normalize the heuristic."""
        max_dist = 0.0
        for conn in self.edges:
            z1 = self.zones[conn.zone1]
            z2 = self.zones[conn.zone2]
            dist = math.hypot(z2.x - z1.x, z2.y - z1.y)
            if dist > max_dist:
                max_dist = dist
        # Fallback to 1.0 to prevent division-by-zero on a single-node map
        return max_dist if max_dist > 0 else 1.0
