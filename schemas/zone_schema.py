from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ZoneType(str, Enum):
    """Enumeration of valid zone types for the drone routing network.

    Defines the movement constraints and turn costs associated with
    entering a specific zone.
    """
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class ZoneMetadata(BaseModel):
    """Configuration constraints for a specific zone.

    Attributes:
        zone_type: The classification of the zone affecting movement rules.
        color: An optional single-word color for visualization.
        max_drones: The maximum number of drones allowed simultaneously.
    """
    zone_type: ZoneType = Field(default=ZoneType.NORMAL)
    color: Optional[str] = Field(default=None, pattern=r"^[a-zA-Z]+$")
    max_drones: int = Field(default=1, ge=1)


class ZoneSchema(BaseModel):
    """Data model representing a discrete physical zone in the network.

    Attributes:
        name: The unique identifier for the zone, excluding spaces and dashes.
        x: The horizontal coordinate on the graphical grid.
        y: The vertical coordinate on the graphical grid.
        metadata: The nested capacity and routing constraints.
    """
    name: str = Field(pattern=r"^[^- ]+$")
    x: int
    y: int
    metadata: ZoneMetadata = Field(default_factory=ZoneMetadata)
