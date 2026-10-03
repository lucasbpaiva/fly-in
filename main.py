import sys
import argparse
from parser import MapParser, ParsingError
from graph import Graph


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
        Graph(parsed_map)
        # Always print the required D<ID>-<zone> format to the terminal
        # Toggle visualization based on the flag
        if args.visualize:
            # Initialize pygame and render simulation
            pass
    except (ParsingError, FileNotFoundError, PermissionError, IOError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
