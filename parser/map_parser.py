from typing import Any
from pathlib import Path
from dataclasses import dataclass
from pydantic import ValidationError
from graph_engine import Zone, Connection
from schemas import ZoneSchema, ConnectionSchema


@dataclass
class Map:
    """Data Transfer Object representing a fully validated simulation map.

    Acts as a static snapshot of the parsed environment topology, providing
    the necessary entities to construct the pathfinding graph.

    Attributes:
        nb_drones: Total number of drones participating in the simulation.
        start_zone: The designated origin zone where all drones begin.
        end_zone: The designated destination zone for all drones.
        zones: A dictionary mapping unique zone names to their Zone instances.
        connections: A list of all validated bidirectional transit links.
    """
    nb_drones: int
    start_zone: Zone
    end_zone: Zone
    zones: dict[str, Zone]
    connections: list[Connection]


class ParsingError(Exception):
    """Custom exception for invalid map formatting or constraint violations."""
    ...


class MapParser:
    """Parses and validates map configuration files for the drone simulation.

    Reads raw map text, enforces strict formatting and structural constraints,
    and translates raw strings into validated Pydantic schemas and objects.
    """
    def __init__(self, filepath: str) -> None:
        """Initialize the MapParser and load the target file.

        Args:
            filepath: The string path to the map configuration file.
        """
        self.path = Path(filepath)
        self.content = self.read_file()

    def read_file(self) -> str:
        """Read and decode the content of the target map file.

        Returns:
            The raw string content of the file.

        Raises:
            FileNotFoundError: If the specified path is invalid or missing.
            PermissionError: If the process lacks read access to the file.
            IOError: If an unexpected system error occurs during execution.
        """
        if not self.path.is_file():
            msg: str = f"The path '{self.path}' is not a valid file."
            raise FileNotFoundError(msg)
        try:
            content = self.path.read_text(encoding='utf-8')
            return content
        except PermissionError:
            raise PermissionError(f"Permission denied to read '{self.path}'.")
        except Exception as e:
            msg = f"An error occurred while parsing '{self.path}': {e}"
            raise IOError(msg)

    @staticmethod
    def parse_zone_line(line: str, expected_prefix: str) -> dict[str, Any]:
        """Extracts parameters and metadata from a zone definition line.

        Args:
            line: The raw string line (e.g., 'hub: roof1 3 4 [color=red]')
            expected_prefix: The exact prefix to strip (e.g., 'hub:')

        Returns:
            A dictionary containing 'name', 'x', 'y', and a 'metadata' dict.
        """
        # Strip the prefix (e.g., "start_hub:")
        raw_data = line[len(expected_prefix):].strip()
        # Separate core parameters from the optional metadata block
        core_str = raw_data
        meta_str = ""
        if "[" in raw_data or "]" in raw_data:
            if (
                not raw_data.endswith("]")
                or raw_data.count("[") != 1
                or raw_data.count("]") != 1
            ):
                raise ValueError(
                    "Malformed metadata brackets."
                    " Must format as: [key=val ...]"
                )
            # Split at the bracket and remove the trailing ']'
            core_str, meta_str = raw_data.split("[", 1)
            meta_str = meta_str.rstrip("]")
        # Validate exactly 3 core parameters (<name> <x> <y>)
        core_tokens = core_str.split()
        if len(core_tokens) != 3:
            raise ValueError(
                "Expected exactly 3 parameters (<name> <x> <y>)"
                f", got {len(core_tokens)}"
            )
        name, x_str, y_str = core_tokens
        # Enforce integer coordinates before Pydantic
        if not (x_str.lstrip('-').isdigit() and y_str.lstrip('-').isdigit()):
            raise ValueError(
                f"Coordinates must be integers, got x:'{x_str}', y:'{y_str}'"
            )
        # Assemble the metadata dictionary
        metadata_dict = {}
        if meta_str:
            for token in meta_str.split():
                if (
                    "=" not in token
                    or token.startswith("=")
                    or token.endswith("=")
                ):
                    raise ValueError(
                        f"Malformed metadata token '{token}'."
                        " Expected 'key=value'"
                    )
                key, val = token.split("=", 1)
                metadata_dict[key] = val
        return {
            "name": name,
            "x": int(x_str),
            "y": int(y_str),
            "metadata": metadata_dict
        }

    @staticmethod
    def parse_connection_line(line: str) -> dict[str, Any]:
        """Extracts parameters and metadata from a connection line.

        Args:
            line: The raw string line
                (e.g., 'connection: corridorA-tunnelB [max_link_capacity=2]')

        Returns:
            A dictionary containing 'zone1', 'zone2', and a 'metadata' dict.
        """
        raw_data = line[len("connection:"):].strip()
        # Separate core parameters from the optional metadata block
        core_str = raw_data
        meta_str = ""
        if "[" in raw_data or "]" in raw_data:
            if (
                not raw_data.endswith("]")
                or raw_data.count("[") != 1
                or raw_data.count("]") != 1
            ):
                raise ValueError(
                    "Malformed metadata brackets."
                    " Must format as: [key=val ...]"
                )
            # Split at the bracket and remove the trailing ']'
            core_str, meta_str = raw_data.split("[", 1)
            meta_str = meta_str.rstrip("]")
        # Validate exactly 2 core parameters (<zone1>-<zone2>)
        core_tokens = core_str.split("-")
        if len(core_tokens) != 2:
            raise ValueError(
                "Expected exactly 2 parameters (<zone1>-<zone2>)"
                f", got {len(core_tokens)}"
            )
        zone1 = core_tokens[0].strip()
        zone2 = core_tokens[1].strip()
        if not zone1 or not zone2:
            raise ValueError("Zone names cannot be empty.")
        # Assemble the metadata dictionary
        metadata_dict = {}
        if meta_str:
            for token in meta_str.split():
                if (
                    "=" not in token
                    or token.startswith("=")
                    or token.endswith("=")
                ):
                    raise ValueError(
                        f"Malformed metadata token '{token}'."
                        " Expected 'key=value'"
                    )
                key, val = token.split("=", 1)
                metadata_dict[key] = val
        return {
            "zone1": zone1,
            "zone2": zone2,
            "metadata": metadata_dict
        }

    def parse(self) -> Map:
        """Execute the parsing pipeline to generate a validated Map object.

        Reads the file line-by-line, enforcing sequential constraints (e.g.,
        nb_drones must be declared first), structural uniqueness (no duplicate
        names, coordinates or links), and metadata syntax rules.

        Returns:
            A fully assembled Map dataclass containing the operational
                entities.

        Raises:
            ParsingError: If any formatting error, logical contradiction or
                schema validation failure is detected, formatted with the
                exact line number.
        """
        nb_drones = 0
        start_zone = None
        end_zone = None
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []
        seen_links: set[tuple[str, str]] = set()
        seen_coords: set[tuple[int, int]] = set()
        is_first_valid_line: bool = True
        lines = self.content.splitlines()
        for line_num, raw_line in enumerate(lines, start=1):
            line = raw_line.split('#')[0].strip()
            if not line:
                continue
            try:
                if is_first_valid_line:
                    if not line.startswith("nb_drones:"):
                        raise ValueError(
                            "The first line must define the number of drones"
                            " using nb_drones: <positive_integer>"
                        )
                    raw_val = line.split(":", 1)[1].strip()
                    if not raw_val.isdigit() or int(raw_val) <= 0:
                        raise ValueError(
                            "nb_drones must be a positive integer,"
                            f" got '{raw_val}'"
                        )
                    nb_drones = int(raw_val)
                    is_first_valid_line = False
                    continue
                if line.startswith("nb_drones:"):
                    m = "nb_drones can only be defined once at the first line"
                    raise ValueError(m)
                if line.startswith("start_hub:"):
                    if start_zone is not None:
                        msg = "There must be exactly one start_hub zone"
                        raise ValueError(msg)
                    raw_dict = self.parse_zone_line(line, "start_hub:")
                    schema = ZoneSchema(**raw_dict)
                    if schema.name in zones:
                        raise ValueError(
                            "Duplicate zone definition: "
                            f"'{schema.name}' already exists."
                        )
                    coords = (schema.x, schema.y)
                    if coords in seen_coords:
                        raise ValueError(
                            f"Duplicate coordinates {coords} for "
                            f"zone '{schema.name}'"
                        )
                    seen_coords.add(coords)
                    start_zone = Zone(schema, is_start=True)
                    zones[schema.name] = start_zone
                elif line.startswith("end_hub:"):
                    if end_zone is not None:
                        msg = "There must be exactly one end_hub zone"
                        raise ValueError(msg)
                    raw_dict = self.parse_zone_line(line, "end_hub:")
                    schema = ZoneSchema(**raw_dict)
                    if schema.name in zones:
                        raise ValueError(
                            "Duplicate zone definition: "
                            f"'{schema.name}' already exists."
                        )
                    coords = (schema.x, schema.y)
                    if coords in seen_coords:
                        raise ValueError(
                            f"Duplicate coordinates {coords} for "
                            f"zone '{schema.name}'"
                        )
                    seen_coords.add(coords)
                    end_zone = Zone(schema, is_end=True)
                    zones[schema.name] = end_zone
                elif line.startswith("hub:"):
                    raw_dict = self.parse_zone_line(line, "hub:")
                    schema = ZoneSchema(**raw_dict)
                    if schema.name in zones:
                        raise ValueError(
                            "Duplicate zone definition: "
                            f"'{schema.name}' already exists."
                        )
                    coords = (schema.x, schema.y)
                    if coords in seen_coords:
                        raise ValueError(
                            f"Duplicate coordinates {coords} for "
                            f"zone '{schema.name}'"
                        )
                    seen_coords.add(coords)
                    zones[schema.name] = Zone(schema)
                elif line.startswith("connection:"):
                    raw_dict = self.parse_connection_line(line)
                    conn_schema = ConnectionSchema(**raw_dict)
                    if (
                        conn_schema.zone1 not in zones
                        or conn_schema.zone2 not in zones
                    ):
                        raise ValueError(
                            "Connection contains an unknown zone: "
                            f"{conn_schema.zone1}-{conn_schema.zone2}"
                        )
                    link_id = (conn_schema.zone1, conn_schema.zone2)
                    if link_id in seen_links:
                        raise ValueError(
                            "Duplicate connection detected: "
                            f"{conn_schema.zone1}-{conn_schema.zone2}"
                        )
                    seen_links.add(link_id)
                    connections.append(Connection(conn_schema))
                else:
                    raise ValueError(f"Unknown directive: {line}")
            except ValidationError as e:
                for err in e.errors():
                    # If it's a field-level error, loc has items
                    if err['loc']:
                        msg = f"{err['loc'][0]}: {err['msg']}"
                    # If it's a model-level error from @model_validator,
                    # loc is empty
                    else:
                        msg = err['msg'].replace("Value error, ", "")
                    raise ParsingError(f"Error on line {line_num}: {msg}")
            except ValueError as e:
                raise ParsingError(f"Error on line {line_num}: {str(e)}")
        if not start_zone or not end_zone:
            raise ParsingError(
                "Map must contain exactly one start_hub and one end_hub."
            )
        return Map(
            nb_drones=nb_drones,
            start_zone=start_zone,
            end_zone=end_zone,
            zones=zones,
            connections=connections
        )
