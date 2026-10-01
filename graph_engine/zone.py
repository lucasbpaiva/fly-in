import sys
from schemas import ZoneSchema, ZoneType


class Zone:
    """Represents a discrete physical node within the drone routing network.

    Manages the state, capacity limits, and current drone occupancy of a
    specific location during the turn-based simulation.

    Attributes:
        name: The unique string identifier for the zone.
        type: The classification determining movement constraints and costs.
        capacity: The maximum number of drones allowed simultaneously.
        occupants: A set of drone identifiers currently located in the zone.
        is_start: Flag indicating if this is the initial origin point.
        is_end: Flag indicating if this is the final destination point.
        is_full: Dynamic flag evaluating if the zone has reached its capacity.
    """
    def __init__(
        self, zone: ZoneSchema, is_start: bool = False, is_end: bool = False
    ) -> None:
        """Initialize a new Zone instance from a validated Pydantic schema.

        Args:
            zone: The validated data model containing
                zone coordinates and metadata.
            is_start: If True, overrides capacity to infinite
                and marks as origin.
            is_end: If True, overrides capacity to infinite
                and marks as destination.
        """
        self.name: str = zone.name
        self.x: int = zone.x
        self.y: int = zone.y
        self.type: ZoneType = zone.metadata.zone
        self.capacity: int = zone.metadata.max_drones
        self.is_start: bool = is_start
        self.is_end: bool = is_end
        if self.is_start or self.is_end:
            self.capacity = sys.maxsize
        self.occupants: set[str] = set()
        self.is_full: bool = len(self.occupants) >= self.capacity

    def can_enter(self) -> bool:
        """Evaluate if the zone can accept an additional drone.

        Returns:
            True if the current occupancy is strictly less than the capacity,
            False otherwise.
        """
        return len(self.occupants) < self.capacity

    def add_drone(self, drone: str) -> None:
        """Register a drone's arrival into the zone and update occupancy state.

        Args:
            drone: The unique identifier of the entering drone.

        Raises:
            ValueError: If the zone is already at maximum capacity.
        """
        if self.is_full:
            raise ValueError(f"Capacity exceeded in zone {self.name}")
        self.occupants.add(drone)
        if len(self.occupants) == self.capacity:
            self.is_full = True

    def remove_drone(self, drone: str) -> None:
        """Process a drone's departure from the zone and free up capacity.

        Args:
            drone: The unique identifier of the departing drone.

        Raises:
            KeyError: If the specified drone is not currently in the zone.
        """
        self.occupants.remove(drone)
        self.is_full = False
