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
            return 5
        zone_type = getattr(node, "type", "normal").lower()
        if zone_type == "priority":
            return 1
        if zone_type == "normal":
            return 2
        if zone_type == "restricted":
            return 5
        return 2  # Fallback

    def _get_valid_neighbors(
        self, node: Zone | Connection
    ) -> list[Zone | Connection]:
        """Fetch adjacent nodes, completely ignoring blocked zones."""
        ...

    def calculate_a_star(
        self, start_node: Zone, end_node: Zone
    ) -> list[Zone | Connection]:
        """
        """
        open_set = []
        # Priority queue stores tuples of (f_score, unique_id, Node)
        # We use id(node) as a tie-breaker if two f_scores are identical
        heapq.heappush(open_set, (0, id(start_node), start_node))
        g_scores = {start_node: 0}
        came_from = {}
        while open_set:
            curr_f, _, curr = heapq.heappop(open_set)
            if curr == end_node:
                return self.reconstruct_path(came_from, curr)
            for neighbor in self._get_valid_neighbors(curr):
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
            # Placeholder for your actual A* algorithm
            # e.g., drone.planned_path = self.calculate_a_star(...)
            pass

    def recalculate_routes(self) -> bool:
        """Attempt to resolve a deadlock by routing around stalled drones."""
        # Clear existing queues for active drones
        for drone in self.engine.active_drones:
            drone.planned_path.clear()
        # Rerun your A* algorithm from their CURRENT locations
        for drone in self.engine.active_drones:
            new_path = self.calculate_a_star(
                start_node=drone.location,
                end_node=self.engine.graph.end_zone
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
