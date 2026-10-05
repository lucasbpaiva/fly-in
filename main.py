import sys
import argparse
from graph import Graph
from simulation import SimulationEngine, Pathfinder
from parser import MapParser, ParsingError


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
                print(" ".join(successful_moves))
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
