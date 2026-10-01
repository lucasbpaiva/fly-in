from pydantic import BaseModel, Field, model_validator, ConfigDict


class ConnectionMetadata(BaseModel):
    """Configuration constraints for a connection between two zones.

    Attributes:
        max_link_capacity: The maximum number of drones that can traverse
            this edge simultaneously.
    """
    # Forbids invalid or misspelled keys
    model_config = ConfigDict(extra="forbid")
    max_link_capacity: int = Field(default=1, ge=1)


class ConnectionSchema(BaseModel):
    """Data model representing a bidirectional edge between two zones.

    Attributes:
        zone1: The identifier of the first connected zone.
        zone2: The identifier of the second connected zone.
        metadata: The nested capacity constraints for the transit path.
    """
    zone1: str = Field(pattern=r"^[^- ]+$")
    zone2: str = Field(pattern=r"^[^- ]+$")
    metadata: ConnectionMetadata = Field(default_factory=ConnectionMetadata)

    @model_validator(mode="after")
    def validate_connection(self) -> "ConnectionSchema":
        """Validate the connection and alphabetically sort the zone names.

        Prevents self-referential loops and normalizes bidirectional
        connections (e.g., 'b-a' becomes 'a-b') to simplify duplicate
        tracking during graph construction.

        Raises:
            ValueError: If zone1 and zone2 are identical.

        Returns:
            The validated and normalized connection instance.
        """
        if self.zone1 == self.zone2:
            raise ValueError("Cannot link zone to itself")
        # Alphabetically sort the zones in a connection to guarantee
        # consistent bidirectional representation
        if self.zone1 > self.zone2:
            self.zone1, self.zone2 = self.zone2, self.zone1
        return self
