import pytest
from pydantic import ValidationError
from schemas import (
    ZoneSchema,
    ZoneMetadata,
    ConnectionSchema,
    ConnectionMetadata,
    ZoneType
)


class TestZoneSchema:
    def test_valid_zone_creation(self) -> None:
        """Verify valid zone names and integer coordinates."""
        zone = ZoneSchema(name="corridorA", x=4, y=3)
        assert zone.name == "corridorA"
        assert zone.x == 4
        assert zone.y == 3
        assert zone.metadata.max_drones == 1  # Relies on nested default

    @pytest.mark.parametrize("invalid_name", ["roof-1", "roof 1", "roof_1-a"])
    def test_invalid_zone_names(self, invalid_name: str) -> None:
        """Zone names must not contain spaces or dashes."""
        with pytest.raises(ValidationError) as exc_info:
            ZoneSchema(name=invalid_name, x=1, y=1)
        error_msg = str(exc_info.value).lower()
        assert (
            "should match pattern" in error_msg
            or "string_pattern_mismatch" in error_msg
        )


class TestZoneMetadata:
    def test_default_values(self) -> None:
        """Verify default metadata tags match the subject constraints."""
        meta = ZoneMetadata()
        assert meta.zone_type == ZoneType.NORMAL
        assert meta.color is None
        assert meta.max_drones == 1

    def test_valid_custom_metadata(self) -> None:
        """Verify valid overriding of metadata fields."""
        meta = ZoneMetadata(
            zone_type=ZoneType.RESTRICTED, color="red", max_drones=5
        )
        assert meta.zone_type == ZoneType.RESTRICTED
        assert meta.color == "red"
        assert meta.max_drones == 5

    @pytest.mark.parametrize("invalid_capacity", [0, -1, -50])
    def test_invalid_max_drones_capacity(self, invalid_capacity: int) -> None:
        """Capacities must be positive integers."""
        with pytest.raises(ValidationError) as exc_info:
            ZoneMetadata(max_drones=invalid_capacity)
        error_msg = str(exc_info.value).lower()
        assert (
                "greater_than_equal" in error_msg
                or "input should be greater than or equal to 1" in error_msg
        )

    def test_invalid_zone_type(self) -> None:
        """Zone types must strictly belong to the allowed Enum."""
        with pytest.raises(ValidationError):
            # Pyright/mypy will catch this statically,
            # but Pydantic must catch runtime casting
            ZoneMetadata(zone_type="magical")  # type: ignore


class TestConnectionSchema:
    def test_default_connection(self) -> None:
        """Verify connections default to a max capacity of 1."""
        conn = ConnectionSchema(zone1="hub", zone2="roof1")
        assert conn.zone1 == "hub"
        assert conn.zone2 == "roof1"
        assert conn.metadata.max_link_capacity == 1

    @pytest.mark.parametrize("invalid_capacity", [0, -2])
    def test_invalid_link_capacity(self, invalid_capacity: int) -> None:
        """Connection capacities must be positive integers."""
        with pytest.raises(ValidationError):
            ConnectionMetadata(max_link_capacity=invalid_capacity)

    def test_identical_zone_connection(self) -> None:
        """A connection should not link a zone to itself."""
        with pytest.raises(ValidationError):
            ConnectionSchema(zone1="hub", zone2="hub")
