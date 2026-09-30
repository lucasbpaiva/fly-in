from typing import Any
from pathlib import Path
from dataclasses import dataclass
from graph_engine import Zone, Connection
from schemas import ZoneSchema, ConnectionSchema


@dataclass
class Map:
    nb_drones: int
    start_zone: Zone
    end_zone: Zone
    zones: dict[str, Zone]
    connections: list[Connection]


class ParsingError(Exception):
    ...


class MapParser:
    def __init__(self, filepath: str) -> None:
        self.path = Path(filepath)
        self.content = self.read_file()

    def read_file(self) -> str:
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

    def parse(self) -> Map:
        nb_drones = 0
        start_zone = None
        end_zone = None
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []
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
                    start_zone = Zone(schema, is_start=True)
                    zones[schema.name] = start_zone
                elif line.startswith("end_hub:"):
                    if end_zone is not None:
                        msg = "There must be exactly one end_hub zone"
                        raise ValueError(msg)
                    # Extract metadata, create ZoneSchema, create Zone(schema, is_end=True)
                    # Assign to end_zone and add to zones dict
                    pass
                elif line.startswith("hub:"):
                    # Extract metadata, create ZoneSchema, create Zone(schema)
                    # Add to zones dict
                    pass
                elif line.startswith("connection:"):
                    # Extract string, create ConnectionSchema
                    # CRITICAL: Verify schema.zone1 and schema.zone2 exist in `zones` dict
                    # Create Connection(schema) and append to connections list
                    pass
                else:
                    raise ValueError(f"Unknown directive: {line}")
            except Exception as e:
                # Catch Pydantic ValidationErrors or custom ValueErrors here
                # Re-raise as a custom ParsingError with line_num
                raise ParsingError(f"Error on line {line_num}: {str(e)}")
        # Final Graph Verification
        if not nb_drones:
            raise ParsingError("Missing nb_drones definition.")
        if not start_zone or not end_zone:
            raise ParsingError("Map must contain exactly one start_hub and one end_hub.")
        return Map(
            nb_drones=nb_drones,
            start_zone=start_zone,
            end_zone=end_zone,
            zones=zones,
            connections=connections
        )
