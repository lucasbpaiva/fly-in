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
        self.graph = self.engine.graph
        # Tracks how many drones are in a specific node at a specific turn
        # Format: {(node_name, turn_number): planned_occupancy_count}
        self.reservations: dict[tuple[str, int], int] = {}

    def _increment_reservations(self, node_name: str, turn: int) -> None:
        """Increment the reservations dict by 1 for (node_name, turn) key."""
        key = (node_name, turn)
        self.reservations[key] = self.reservations.get(key, 0) + 1

    def _is_available(self, node: Zone | Connection, turn: int) -> bool:
        """Check if a node has capacity at a specific future turn."""
        planned_occupancy = self.reservations.get((node.name, turn), 0)
        return planned_occupancy < node.capacity

    def _reserve_path(self, path: list[Zone | Connection]) -> None:
        """Lock in a drone's route to block future A* calculations."""
        for turn, node in enumerate(path):
            self._increment_reservations(node.name, turn)
            if turn > 0:
                prev = path[turn - 1]
                both_zones = isinstance(prev, Zone) and isinstance(node, Zone)
                if both_zones and prev != node:
                    conn = self.graph.get_connection(prev.name, node.name)
                    if conn:
                        self._increment_reservations(conn.name, turn)

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
        x1, y1 = self.graph.get_coords(current_node)
        x2, y2 = self.graph.get_coords(target_node)
        euclidean_distance = math.hypot(x2 - x1, y2 - y1)
        return euclidean_distance / self.graph.max_edge_length

    def reconstruct_path(
        self,
        came_from: dict[
            tuple[Zone | Connection, int], tuple[Zone | Connection, int]
        ],
        current: tuple[Zone | Connection, int]
    ) -> list[Zone | Connection]:
        """Reconstruct the cheapest route by tracing the predecessor dict.

        Args:
            came_from: A mapping of nodes to their immediate predecessor.
            current: The destination node where the algorithm finished.

        Returns:
            The sequential path from the starting location to the target.
        """
        cheapest_path = [current[0]]
        while current in came_from:
            current = came_from[current]
            cheapest_path.append(current[0])
        return cheapest_path[::-1]

    def cooperative_a_star(
        self, start_node: Zone | Connection, end_node: Zone | Connection
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
        # Queue format: (f_time, f_preference, tiebreaker, node, turn)
        open_set: list[tuple[float, int, int, Zone | Connection, int]] = []
        heapq.heappush(open_set, (0, 0, id(start_node), start_node, 0))
        g_scores = {(start_node, 0): 0}
        came_from: dict[
            tuple[Zone | Connection, int], tuple[Zone | Connection, int]
        ] = {}
        while open_set:
            _, _, _, curr, curr_turn = heapq.heappop(open_set)
            if curr == end_node:
                return self.reconstruct_path(came_from, (curr, curr_turn))
            neighbors = self.graph.get_neighbors(curr)
            neighbors.append(curr)  # "Wait" action
            for neighbor in neighbors:
                is_waiting = (neighbor == curr)
                next_turn = curr_turn + 1
                if is_waiting and isinstance(curr, Connection):
                    continue
                if not self._is_available(neighbor, next_turn):
                    continue
                if (
                    not is_waiting
                    and isinstance(curr, Zone)
                    and isinstance(neighbor, Zone)
                ):
                    conn = self.graph.get_connection(curr.name, neighbor.name)
                    if conn and not self._is_available(conn, next_turn):
                        continue
                step_cost = 1 if is_waiting else self._get_step_cost(neighbor)
                g_score = g_scores[(curr, curr_turn)] + step_cost
                next_state = (neighbor, next_turn)
                if g_score < g_scores.get(next_state, float('inf')):
                    came_from[next_state] = (curr, curr_turn)
                    g_scores[next_state] = g_score
                    h_score = int(self._heuristic(neighbor, end_node))
                    f_score = next_turn + h_score
                    entry = (
                        f_score, g_score, id(neighbor), neighbor, next_turn
                    )
                    heapq.heappush(open_set, entry)
        return []  # Unsolvable

    def precompute_routes(self) -> None:
        """Route drones sequentially so they respect each other's schedules."""
        self.reservations.clear()
        drones = self.engine.active_drones
        start_node = self.graph.start_zone
        end_node = self.graph.end_zone
        for drone in drones:
            path = self.cooperative_a_star(start_node, end_node)
            if path:
                self._reserve_path(path)
                drone.planned_path = deque(path[1:])
            else:
                print(f"Warning: No valid path found for {drone.id}")

    def recalculate_routes(self) -> bool:
        """Attempt to resolve a deadlock using Cooperative A* from mid-map."""
        self.reservations.clear()
        drones = self.engine.active_drones
        for drone in drones:
            drone.planned_path.clear()
            for future_turn in range(0, 100):  # 100 is an arbitrary turn limit
                self._increment_reservations(drone.location.name, future_turn)
        end_zone = self.graph.end_zone
        for drone in drones:
            for future_turn in range(0, 100):
                node_key = (drone.location.name, future_turn)
                self.reservations[node_key] -= 1
            path = self.cooperative_a_star(drone.location, end_zone)
            if not path:
                return False
            self._reserve_path(path)
            drone.planned_path = deque(path[1:])
        return True

    def get_next_moves(self) -> dict[str, Zone | Connection]:
        """Extract the immediate next step for all active drones."""
        planned_moves = {}
        for drone in self.engine.active_drones:
            if drone.planned_path:
                next_node = drone.planned_path[0]
                if next_node == drone.location:
                    drone.planned_path.popleft()
                else:
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
