import pytest
from schemas import (
    ZoneSchema, ZoneMetadata, ConnectionSchema, ConnectionMetadata, ZoneType
)
from graph import Zone, Connection, Map, Graph
# Assuming your engine will be in simulation.py
from simulation import SimulationEngine


@pytest.fixture
def linear_graph() -> Graph:
    """Fixture providing a simple linear map: start -> hub_a -> end."""
    z_meta = ZoneMetadata(zone=ZoneType.NORMAL, max_drones=1)

    start = Zone(
        ZoneSchema(name="start", x=0, y=0, metadata=z_meta), is_start=True
    )
    hub_a = Zone(ZoneSchema(name="hub_a", x=1, y=0, metadata=z_meta))
    end = Zone(ZoneSchema(name="end", x=2, y=0, metadata=z_meta), is_end=True)

    zones = {"start": start, "hub_a": hub_a, "end": end}

    c_meta = ConnectionMetadata(max_link_capacity=1)
    c1 = Connection(
        ConnectionSchema(zone1="start", zone2="hub_a", metadata=c_meta)
    )
    c2 = Connection(
        ConnectionSchema(zone1="hub_a", zone2="end", metadata=c_meta)
    )

    map_dto = Map(
        nb_drones=2,
        start_zone=start,
        end_zone=end,
        zones=zones,
        connections=[c1, c2]
    )
    return Graph(parsed_map=map_dto)


class TestSimulationEngine:
    """Tests for the SimulationEngine class."""
    def test_engine_initialization(self, linear_graph: Graph) -> None:
        """Verify the engine correctly spawns drones and sets initial state."""
        engine = SimulationEngine(graph=linear_graph)

        assert engine.turn == 0
        assert engine.is_finished is False
        assert len(engine.drones) == 2

        # All drones must spawn in the start zone
        assert "D1" in linear_graph.start_zone.occupants
        assert "D2" in linear_graph.start_zone.occupants

        # Drone location tracking should reflect the start zone
        assert engine.drones["D1"].location == linear_graph.start_zone
        assert engine.drones["D2"].location == linear_graph.start_zone

    def test_valid_movement_execution(self, linear_graph: Graph) -> None:
        """Verify the engine correctly moves a drone and updates capacities."""
        engine = SimulationEngine(graph=linear_graph)
        target_node = linear_graph.zones["hub_a"]

        # Engine attempts to move D1 to hub_a
        success = engine.attempt_move(drone_id="D1", target=target_node)

        assert success is True
        assert "D1" in target_node.occupants
        assert "D1" not in linear_graph.start_zone.occupants
        assert engine.drones["D1"].location == target_node

    def test_capacity_rejection(self, linear_graph: Graph) -> None:
        """Verify engine blocks movement if the target node is at capacity."""
        engine = SimulationEngine(graph=linear_graph)
        target_node = linear_graph.zones["hub_a"]

        # Move D1 into hub_a (capacity = 1)
        engine.attempt_move(drone_id="D1", target=target_node)
        assert target_node.is_full is True

        # Attempt to move D2 into the full hub_a
        success = engine.attempt_move(drone_id="D2", target=target_node)

        assert success is False
        assert "D2" not in target_node.occupants
        assert "D2" in linear_graph.start_zone.occupants  # D2 stays behind

    def test_turn_output_generation(self, linear_graph: Graph) -> None:
        """Verify the standard output string has format D<ID>-<zone>."""
        engine = SimulationEngine(graph=linear_graph)
        target_node = linear_graph.zones["hub_a"]

        # Execute a turn where only D1 moves
        moves = {"D1": target_node}  # Planned moves dictionary
        output = engine.play_turn(moves)

        # Output should only contain drones that successfully moved this turn
        assert output == "D1-hub_a"
        assert engine.turn == 1

    def test_simulation_completion(self, linear_graph: Graph) -> None:
        """Verify drones reaching the end_zone are marked as finished."""
        engine = SimulationEngine(graph=linear_graph)
        # Teleport D1 and D2 to the end zone for the test
        engine.drones["D1"].location = linear_graph.end_zone
        engine.drones["D2"].location = linear_graph.end_zone
        # Call the cleanup/completion check method
        engine.check_completions()
        assert engine.drones["D1"].is_finished is True
        assert engine.drones["D2"].is_finished is True
        assert len(engine.active_drones) == 0
        assert engine.is_finished is True
