from graph import Zone, Connection


class Drone:
    """Class Drone."""
    def __init__(self, drone_id: str, initial_location: Zone) -> None:
        """Constructor method."""
        self.id: str = drone_id
        self.location: Zone | Connection = initial_location
        self.is_finished: bool = False
        self.planned_path: list[Zone | Connection] = []
