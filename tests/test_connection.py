import pytest
from schemas import ConnectionSchema, ConnectionMetadata
from graph import Connection


@pytest.fixture
def default_connection_schema() -> ConnectionSchema:
    meta = ConnectionMetadata(max_link_capacity=1)
    return ConnectionSchema(zone1="hub", zone2="roof1", metadata=meta)


@pytest.fixture
def high_capacity_connection_schema() -> ConnectionSchema:
    meta = ConnectionMetadata(max_link_capacity=3)
    return ConnectionSchema(zone1="corridorA", zone2="tunnelB", metadata=meta)


class TestConnectionState:
    def test_connection_initialization(
        self, default_connection_schema: ConnectionSchema
    ) -> None:
        """Verify the OOP domain object correctly maps the Pydantic schema."""
        conn = Connection(default_connection_schema)
        # "hub" and "roof1" are already sorted alphabetically (h < r).
        assert conn.zone1 == "hub"
        assert conn.zone2 == "roof1"
        assert conn.capacity == 1
        assert conn.occupants == set()
        assert conn.is_full is False

    def test_add_and_remove_drone(
        self, high_capacity_connection_schema: ConnectionSchema
    ) -> None:
        """Verify drones can correctly enter and leave a connection in transit."""
        conn = Connection(high_capacity_connection_schema)
        assert conn.can_enter() is True
        conn.add_drone("D1")
        conn.add_drone("D2")
        assert "D1" in conn.occupants
        assert "D2" in conn.occupants
        assert conn.is_full is False  # Capacity is 3
        conn.remove_drone("D1")
        assert "D1" not in conn.occupants
        assert len(conn.occupants) == 1

    def test_capacity_rejection(
        self, default_connection_schema: ConnectionSchema
    ) -> None:
        """Verify the connection strictly rejects entry if it would exceed max_link_capacity."""
        conn = Connection(default_connection_schema)  # capacity = 1
        conn.add_drone("D1")
        assert conn.is_full is True
        assert conn.can_enter() is False
        with pytest.raises(ValueError, match=r"^Capacity exceeded"):
            conn.add_drone("D2")

    def test_cannot_remove_nonexistent_drone(
        self, default_connection_schema: ConnectionSchema
    ) -> None:
        """Attempting to remove a drone that isn't on the connection should raise an error."""
        conn = Connection(default_connection_schema)
        with pytest.raises(KeyError):
            conn.remove_drone("D99")
