from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ZoneType(str, Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class ZoneMetadata(BaseModel):
    zone_type: ZoneType = Field(default=ZoneType.NORMAL)
    color: Optional[str] = Field(default=None, pattern=r"^[a-zA-Z]+$")
    max_drones: int = Field(default=1, ge=1)


class ZoneSchema(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[^- ]+$")
    x: int
    y: int
    metadata: ZoneMetadata = Field(default_factory=ZoneMetadata)
