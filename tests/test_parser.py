import pytest
from pathlib import Path
# Assuming the parser will be structured as a class in parser.py
# and return a structured object like ParsedMap containing the schemas.
from parser import MapParser, ParsingError
from schemas import ZoneType


@pytest.fixture
def valid_map_content() -> str:
    """Define a valid map."""
    return """# This is a comment
            nb_drones: 5
            start_hub: hub 0 0 [color=green]
            end_hub: goal 10 10 [color=yellow]
            hub: roof1 3 4 [zone=restricted color=red]
            hub: roof2 6 2
            connection: hub-roof1 [max_link_capacity=2]
            connection: roof1-roof2
            connection: roof2-goal
            """


class TestMapParser:
    """Define tests for the parser."""
    def test_parse_valid_map(
        self, tmp_path: Path, valid_map_content: str
    ) -> None:
        """Verify parser correctly extracts all components of a valid map."""
        map_file = tmp_path / "valid.map"
        map_file.write_text(valid_map_content)
        parser = MapParser(filepath=str(map_file))
        parsed_data = parser.parse()
        assert parsed_data.nb_drones == 5
        # Verify Start and End
        assert parsed_data.start_zone.name == "hub"
        assert parsed_data.end_zone.name == "goal"
        # Verify Standard Hubs
        assert "roof1" in parsed_data.zones
        assert parsed_data.zones["roof1"].type == ZoneType.RESTRICTED
        assert parsed_data.zones["roof1"].x == 3
        assert "roof2" in parsed_data.zones
        assert parsed_data.zones["roof2"].type == ZoneType.NORMAL
        # Verify Connections
        assert len(parsed_data.connections) == 3
        assert parsed_data.connections[0].capacity == 2

    def test_missing_drones_definition(self, tmp_path: Path) -> None:
        """The first line (ignoring comments) must define nb_drones."""
        content = """start_hub: hub 0 0
            end_hub: goal 10 10
            connection: hub-goal"""
        map_file = tmp_path / "missing_drones.map"
        map_file.write_text(content)
        with pytest.raises(ParsingError, match="nb_drones"):
            MapParser(filepath=str(map_file)).parse()

    @pytest.mark.parametrize("missing_hub", [
        "start_hub: hub 0 0",
        "end_hub: goal 10 10"
    ])
    def test_missing_start_or_end_hub(
        self, tmp_path: Path, missing_hub: str
    ) -> None:
        """The map must contain exactly one start_hub and one end_hub."""
        content = f"""nb_drones: 2\n{missing_hub}"""
        map_file = tmp_path / "missing_hub.map"
        map_file.write_text(content)
        with pytest.raises(
            ParsingError, match="exactly one start_hub and one end_hub"
        ):
            MapParser(filepath=str(map_file)).parse()

    def test_duplicate_connections_rejected(self, tmp_path: Path) -> None:
        """Same connection must not appear more than once (a-b and b-a)."""
        content = """nb_drones: 2
            start_hub: a 0 0
            end_hub: b 1 1
            connection: a-b
            connection: b-a"""
        map_file = tmp_path / "duplicates.map"
        map_file.write_text(content)
        with pytest.raises(ParsingError, match="Duplicate"):
            MapParser(filepath=str(map_file)).parse()

    def test_undeclared_zone_in_connection(self, tmp_path: Path) -> None:
        """Connections must only link previously defined zones."""
        content = """nb_drones: 2
            start_hub: a 0 0
            end_hub: b 1 1
            connection: a-ghost_zone"""
        map_file = tmp_path / "ghost.map"
        map_file.write_text(content)
        with pytest.raises(ParsingError, match="unknown zone"):
            MapParser(filepath=str(map_file)).parse()

    def test_invalid_metadata_syntax(self, tmp_path: Path) -> None:
        """Malformed metadata brackets should trigger a parsing error."""
        content = """nb_drones: 2
            start_hub: a 0 0 [color=green
            end_hub: b 1 1"""
        map_file = tmp_path / "bad_meta.map"
        map_file.write_text(content)
        with pytest.raises(ParsingError):
            MapParser(filepath=str(map_file)).parse()
