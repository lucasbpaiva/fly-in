import sys
import pytest
from schemas import ZoneSchema, ZoneMetadata, ZoneType
from graph_engine import Zone


@pytest.fixture
def normal_zone_schema() -> ZoneSchema:
    meta = ZoneMetadata(zone=ZoneType.NORMAL, max_drones=2)
    return ZoneSchema(name="roof1", x=3, y=4, metadata=meta)


@pytest.fixture
def restricted_zone_schema() -> ZoneSchema:
    meta = ZoneMetadata(zone=ZoneType.RESTRICTED, max_drones=1)
    return ZoneSchema(name="corridorA", x=0, y=0, metadata=meta)


class TestZoneState:
    def test_zone_initialization(self, normal_zone_schema: ZoneSchema) -> None:
        """Verify the OOP domain object correctly maps the Pydantic schema."""
        zone = Zone(normal_zone_schema)
        assert zone.name == "roof1"
        assert zone.type == ZoneType.NORMAL
        assert zone.capacity == 2
        assert zone.occupants == set()  # Using a set for O(1) drone lookups
        assert zone.is_full is False

    def test_start_and_end_hub_infinite_capacity(
        self, normal_zone_schema: ZoneSchema
    ) -> None:
        """The max_drones limit must be ignored for start and end hubs."""
        # Even though the schema says max_drones=2,
        # flagging it as start/end overrides this
        start_zone = Zone(normal_zone_schema, is_start=True)
        end_zone = Zone(normal_zone_schema, is_end=True)
        assert start_zone.capacity == sys.maxsize
        assert end_zone.capacity == sys.maxsize

    def test_add_and_remove_drone(
        self, normal_zone_schema: ZoneSchema
    ) -> None:
        """Verify drones can correctly enter and leave a zone."""
        zone = Zone(normal_zone_schema)

        assert zone.can_enter() is True
        zone.add_drone("D1")
        assert "D1" in zone.occupants

        zone.remove_drone("D1")
        assert "D1" not in zone.occupants

    def test_capacity_rejection(
        self, restricted_zone_schema: ZoneSchema
    ) -> None:
        """Verify the zone strictly rejects entry if it exceeds max_drones."""
        zone = Zone(restricted_zone_schema)  # max_drones = 1
        zone.add_drone("D1")
        assert zone.is_full is True
        assert zone.can_enter() is False
        with pytest.raises(ValueError, match="Capacity exceeded"):
            zone.add_drone("D2")

    def test_cannot_remove_nonexistent_drone(
        self, normal_zone_schema: ZoneSchema
    ) -> None:
        """Attempting to remove a drone that isn't in the zone should raise an error."""
        zone = Zone(normal_zone_schema)

        with pytest.raises(KeyError):
            zone.remove_drone("D99")
