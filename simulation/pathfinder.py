import math
import heapq
from collections import deque
from graph import Zone, Connection
from .engine import SimulationEngine


class Pathfinder:
    """Calculates and manages routing logic for all drones in the simulation.

    Acts as the intelligent routing controller, decoupling the pathfinding
    algorithm from the physical movement resolution handled by the simulation
    engine.
    """
    def __init__(self, engine: SimulationEngine) -> None:
        """Initialize the pathfinder with a reference to the simulation engine.

        Args:
            engine: The central simulation engine used to evaluate graph
                topology, query active drone states, and monitor physical
                capacities.
        """
        self.engine = engine

    def _get_step_cost(self, node: Zone | Connection) -> int:
        """Return the traversal weight based on the node's classification."""
        if isinstance(node, Connection):
            return 2
        zone_type = getattr(node, "type", "normal").lower()
        if zone_type == "priority":
            return 1
        else:  # normal or restricted
            return 2

    def _heuristic(
        self, current_node: Zone | Connection, target_node: Zone | Connection
    ) -> float:
        """Calculate the admissible minimum turn cost to the target node."""
        x1, y1 = self.engine.graph.get_coords(current_node)
        x2, y2 = self.engine.graph.get_coords(target_node)
        euclidean_distance = math.hypot(x2 - x1, y2 - y1)
        return euclidean_distance / self.engine.graph.max_edge_length

    def _reconstruct_path(
        self,
        came_from: dict[Zone | Connection, Zone | Connection],
        current: Zone | Connection
    ) -> list[Zone | Connection]:
        """Reconstruct the cheapest route by tracing the predecessor dict.

        Args:
            came_from: A mapping of nodes to their immediate predecessor.
            current: The destination node where the algorithm finished.

        Returns:
            The sequential path from the starting location to the target.
        """
        cheapest_path = [current]
        while current in came_from:
            current = came_from[current]
            cheapest_path.append(current)
        return cheapest_path[::-1][1:]

    def calculate_a_star(
        self,
        start_node: Zone | Connection,
        end_node: Zone | Connection,
        avoid_nodes: set[Zone | Connection] | None = None
    ) -> list[Zone | Connection]:
        """Calculate the optimal path between two nodes using the A* algorithm.

        Evaluates the graph to find the lowest-cost route from the starting
        location to the target by balancing the known traversal cost (g-score)
        against an admissible spatial heuristic (h-score). It dynamically
        accounts for zone classifications (e.g., priority lanes, restricted
        areas) to determine the most efficient physical route.

        Args:
            start_node: The physical location (Zone or Connection) where the
                search begins.
            end_node: The target destination (Zone or Connection) to reach.

        Returns:
            A sequential list of nodes representing the complete path from
            start to finish. Returns an empty list if no valid route exists
            (e.g., a disconnected graph or total gridlock).
        """
        avoid_nodes = avoid_nodes or set()
        open_set: list[tuple[float, int, Zone | Connection]] = []
        # Priority queue stores tuples of (f_score, unique_id, Node)
        # We use id(node) as a tie-breaker if two f_scores are identical
        heapq.heappush(open_set, (0, id(start_node), start_node))
        g_scores = {start_node: 0}
        came_from: dict[Zone | Connection, Zone | Connection] = {}
        while open_set:
            curr = heapq.heappop(open_set)[2]
            if curr == end_node:
                return self._reconstruct_path(came_from, curr)
            for neighbor in self.engine.graph.get_neighbors(curr):
                if neighbor in avoid_nodes:
                    continue
                candidate_g = g_scores[curr] + self._get_step_cost(neighbor)
                if candidate_g < g_scores.get(neighbor, float('inf')):
                    came_from[neighbor] = curr
                    g_scores[neighbor] = candidate_g
                    h_score = self._heuristic(neighbor, end_node)
                    f_score = candidate_g + h_score
                    heapq.heappush(open_set, (f_score, id(neighbor), neighbor))
        return []  # Unsolvable

    def precompute_routes(self) -> None:
        """Run A* to generate the full path for every drone at turn 0."""
        for drone in self.engine.active_drones:
            start_node = self.engine.graph.start_zone
            end_node = self.engine.graph.end_zone
            initial_path = self.calculate_a_star(start_node, end_node)
            drone.planned_path = deque(initial_path)

    def recalculate_routes(self) -> bool:
        """Attempt to resolve a deadlock by routing around stalled drones."""
        # Clear existing queues for active drones
        for drone in self.engine.active_drones:
            drone.planned_path.clear()
        # Rerun your A* algorithm from their CURRENT locations
        for drone in self.engine.active_drones:
            obstacles = set(
                other.location for other in self.engine.active_drones
                if other.id != drone.id
            )
            new_path = self.calculate_a_star(
                start_node=drone.location,
                end_node=self.engine.graph.end_zone,
                avoid_nodes=obstacles
            )
            if not new_path:
                return False  # A* couldn't find a way out
            drone.planned_path = deque(new_path)
        return True

    def get_next_moves(self) -> dict[str, Zone | Connection]:
        """Extract the immediate next step for all active drones."""
        planned_moves = {}
        for drone in self.engine.active_drones:
            if drone.planned_path:
                next_node = drone.planned_path[0]
                planned_moves[drone.id] = next_node
        return planned_moves

    def resolve_completed_moves(self, successful_moves: list[str]) -> None:
        """Pop node from drone's queue only if the engine allowed the move."""
        # successful_moves format is ["D1-hub_a", "D2-hub_a-hub_b"]
        moved_drone_ids = [move.split("-")[0] for move in successful_moves]
        for drone_id in moved_drone_ids:
            path_queue = self.engine.drones[drone_id].planned_path
            if path_queue:
                path_queue.popleft()
