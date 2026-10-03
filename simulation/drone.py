class Drone:
    """Class Drone."""
    def __init__(self, drone_id: str) -> None:
        """Constructor method."""
        self.id = drone_id
        self.is_active = True
