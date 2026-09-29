from schemas import ConnectionSchema


class Connection:
    """Represents a bidirectional transit pathway between two zones.

    Acts as a temporary holding container for drones executing multi-turn
    movements (e.g., traveling to a restricted zone). It enforces the
    max_link_capacity constraint during discrete simulation turns.

    Attributes:
        zone1: The identifier of the first connected zone.
        zone2: The identifier of the second connected zone.
        capacity: The maximum number of drones that can occupy the link.
        occupants: A set of drone identifiers currently traversing the link.
        is_full: Flag evaluating if the connection has reached capacity.
    """
    def __init__(self, connection: ConnectionSchema) -> None:
        """Initialize new Connection instance from a validated Pydantic schema.

        Args:
            connection: The validated data model containing the zones connected
            and metadata.
        """
        self.zone1: str = connection.zone1
        self.zone2: str = connection.zone2
        self.capacity: int = connection.metadata.max_link_capacity
        self.occupants: set[str] = set()
        self.is_full: bool = len(self.occupants) >= self.capacity

    def can_enter(self) -> bool:
        """Evaluate if the connection can accept an additional drone.

        Returns:
            True if the current occupancy is strictly less than the capacity,
            False otherwise.
        """
        return len(self.occupants) < self.capacity

    def add_drone(self, drone: str) -> None:
        """Register a drone's arrival into the connection and update occupancy.

        Args:
            drone: The unique identifier of the entering drone.

        Raises:
            ValueError: If the connection is already at maximum capacity.
        """
        if self.is_full:
            raise ValueError(
                f"Capacity exceeded in connection {self.zone1}-{self.zone2}"
            )
        self.occupants.add(drone)
        if len(self.occupants) == self.capacity:
            self.is_full = True

    def remove_drone(self, drone: str) -> None:
        """Process drone's departure from the connection and free up capacity.

        Args:
            drone: The unique identifier of the departing drone.

        Raises:
            KeyError: If the specified drone is not currently in the zone.
        """
        self.occupants.remove(drone)
        self.is_full = False
