import pytest
from schemas import (
    ZoneSchema, ZoneMetadata, ConnectionSchema, ConnectionMetadata, ZoneType
)
from graph import Zone, Connection, Map, Graph


@pytest.fixture
def valid_map_dto() -> Map:
    """Fixture providing a validated Map data transfer object."""
    z_meta = ZoneMetadata(zone=ZoneType.NORMAL, max_drones=1)

    # Instantiate Zones
    start = Zone(
        ZoneSchema(name="start", x=0, y=0, metadata=z_meta), is_start=True
    )
    hub_a = Zone(ZoneSchema(name="hub_a", x=1, y=1, metadata=z_meta))
    hub_b = Zone(ZoneSchema(name="hub_b", x=2, y=2, metadata=z_meta))
    end = Zone(ZoneSchema(name="end", x=3, y=3, metadata=z_meta), is_end=True)

    zones = {
        "start": start,
        "hub_a": hub_a,
        "hub_b": hub_b,
        "end": end
    }

    # Instantiate Connections
    c_meta = ConnectionMetadata(max_link_capacity=1)
    c1 = Connection(
        ConnectionSchema(zone1="start", zone2="hub_a", metadata=c_meta)
    )
    c2 = Connection(
        ConnectionSchema(zone1="hub_a", zone2="hub_b", metadata=c_meta)
    )
    c3 = Connection(
        ConnectionSchema(zone1="hub_a", zone2="end", metadata=c_meta)
    )

    return Map(
        nb_drones=5,
        start_zone=start,
        end_zone=end,
        zones=zones,
        connections=[c1, c2, c3]
    )


class TestGraph:
    """Tests for the Graph class."""
    def test_graph_initialization(self, valid_map_dto: Map) -> None:
        """Verify the Graph correctly unwraps the Map DTO."""
        graph = Graph(parsed_map=valid_map_dto)

        assert graph.nb_drones == 5
        assert graph.start_zone.name == "start"
        assert graph.end_zone.name == "end"
        assert "hub_a" in graph.zones

    def test_bidirectional_adjacency_list(self, valid_map_dto: Map) -> None:
        """Verify the graph constructs two-way links for every connection."""
        graph = Graph(parsed_map=valid_map_dto)

        # start is connected to hub_a
        start_neighbors = [z.name for z in graph.get_neighbors("start")]
        assert start_neighbors == ["hub_a"]

        # hub_a is connected to start, hub_b, and end
        hub_a_neighbors = [z.name for z in graph.get_neighbors("hub_a")]
        assert "start" in hub_a_neighbors
        assert "hub_b" in hub_a_neighbors
        assert "end" in hub_a_neighbors
        assert len(hub_a_neighbors) == 3

        # end is connected to hub_a
        end_neighbors = [z.name for z in graph.get_neighbors("end")]
        assert end_neighbors == ["hub_a"]

    def test_get_neighbors_invalid_zone(self, valid_map_dto: Map) -> None:
        """Test.

        Requesting neighbors for a non-existent zone should return an empty
        list.
        """
        graph = Graph(parsed_map=valid_map_dto)
        neighbors = graph.get_neighbors("ghost_zone")

        assert neighbors == set()
        assert isinstance(neighbors, set)

    def test_graph_encapsulation(self, valid_map_dto: Map) -> None:
        """Test.

        Verify the adjacency list stores direct references to Zone objects.
        """
        graph = Graph(parsed_map=valid_map_dto)

        neighbors = graph.get_neighbors("start")
        target_zone = next(iter(neighbors))

        # Mutating the returned object should reflect in the central zones
        # dictionary
        target_zone.add_drone("D1")
        assert "D1" in graph.zones["hub_a"].occupants
