import sys
import argparse
from graph import Graph
from simulation import SimulationEngine, Pathfinder
from parser import MapParser, ParsingError

ANSI_COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "blue": "\033[94m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "orange": "\033[38;5;214m",
    "purple": "\033[38;5;129m",
    "brown": "\033[38;5;130m",
    "lime": "\033[38;5;118m",
    "magenta": "\033[35m",
    "gold": "\033[38;5;220m",
    "black": "\033[30m",
    "maroon": "\033[38;5;52m",
    "darkred": "\033[38;5;88m",
    "violet": "\033[38;5;135m",
    "crimson": "\033[38;5;161m",
    "rainbow": "",
    "reset": "\033[0m",
}

RAINBOW_COLORS = [
    "\033[91m",        # Red
    "\033[38;5;214m",  # Orange
    "\033[93m",        # Yellow
    "\033[92m",        # Green
    "\033[94m",        # Blue
    "\033[38;5;57m",   # Indigo
    "\033[38;5;135m"   # Violet
]


def apply_rainbow(text: str) -> str:
    """Applies a repeating ANSI color sequence to each character in a string.

    Iterates through the provided text and wraps each character in a color
    code from the RAINBOW_COLORS list, cycling back to the beginning of the
    list if the text length exceeds the number of available colors. Appends
    an ANSI reset code at the end to prevent color bleeding in the terminal.

    Args:
        text (str): The raw string to be colorized (e.g., a zone name).

    Returns:
        str: The fully formatted string containing interleaved ANSI color
            codes and characters, terminating with a color reset code.
    """
    colored_chars = []
    for i, char in enumerate(text):
        color = RAINBOW_COLORS[i % len(RAINBOW_COLORS)]
        colored_chars.append(f"{color}{char}")
    reset = ANSI_COLORS.get("reset", "\033[0m")
    return "".join(colored_chars) + reset


def print_output(moves: list[str], graph: Graph) -> None:
    """Prints the successful drone moves to the terminal with ANSI colors.

    Processes a list of move strings by parsing the individual node names
    and looking up their color attributes in the graph. Wraps each node in
    the corresponding ANSI escape code before printing. Supports standard
    colors and a character-by-character "rainbow" effect.

    Args:
        moves: A list of executed move strings for the current turn
            (e.g., ["D1-gate1", "D2-waiting_area-goal"]).
        graph: The simulation graph containing the defined zones and
            their metadata, used for color lookups.
    """
    colored_output = []
    for move in moves:
        parts = move.split("-")
        # parts[0] is the Drone ID (e.g., "D1"), leave it uncolored
        colored_parts = [parts[0]]
        for node in parts[1:]:
            zone = graph.zones.get(node)
            if zone and zone.color is not None:
                color_name = zone.color.lower()
                if color_name == "rainbow":
                    colored_parts.append(apply_rainbow(node))
                else:
                    color_code = ANSI_COLORS.get(color_name, "")
                    reset_code = ANSI_COLORS["reset"] if color_code else ""
                    colored_parts.append(f"{color_code}{node}{reset_code}")
            else:
                colored_parts.append(node)
        colored_output.append("-".join(colored_parts))
    print(" ".join(colored_output))


def parse_argv() -> argparse.Namespace:
    """Parse command-line arguments for the drone routing simulation.

    Configures the argument parser to accept a mandatory map file path
    and an optional flag to trigger the graphical visualization engine.

    Returns:
        An object containing the parsed command-line arguments.
        Expected attributes are 'map_file' (str) and 'visualize' (bool).
    """
    parser = argparse.ArgumentParser(description="Drone Routing Simulation")
    # Positional argument for the map file
    example: str = "(e.g., maps/easy/01_linear_path.txt)"
    parser.add_argument("map_file", help=f"Path to the map file {example}")
    # Optional boolean flag to toggle the visualizer
    msg: str = "Enable Pygame visualizer"
    parser.add_argument("-v", "--visualize", action="store_true", help=msg)
    return parser.parse_args()


def main() -> None:
    """Execute the core workflow of the simulation.

    Acts as the main entry point. It fetches command-line arguments,
    initializes the Pydantic parser for the selected map, executes the
    pathfinding algorithm, prints standard terminal output
    and conditionally launches the Pygame interface.
    """
    try:
        args = parse_argv()
        parsed_map = MapParser(args.map_file).parse()
        graph = Graph(parsed_map)
        engine = SimulationEngine(graph)
        pathfinder = Pathfinder(engine)
        pathfinder.precompute_routes()
        while not engine.is_finished:
            requested_moves = pathfinder.get_next_moves()
            successful_moves = engine.play_turn(requested_moves)
            if requested_moves and not successful_moves:
                if not pathfinder.recalculate_routes():
                    print("Error: Unresolvable gridlock")
                    sys.exit(1)
                continue
            pathfinder.resolve_completed_moves(successful_moves)
            if successful_moves:
                print_output(successful_moves, graph)
            if args.visualize:
                for drone in engine.drones.values():
                    # Access the physical node object
                    # to get exact coordinates for the sprite
                    pass
    except (ParsingError, FileNotFoundError, PermissionError, IOError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
