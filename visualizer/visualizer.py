import sys
import math
from graph import Graph, Zone, Connection
from simulation import Drone
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame  # noqa: E402


class Visualizer:
    """A Pygame-based graphical interface for visualizing the drone simulation.

    Manages a resizable 2D canvas that renders physical nodes (zones) and their
    interconnecting paths (edges).
    Features an interactive camera with click-and-drag panning
    and scroll-wheel zooming.

    Attributes:
        COLORS: A mapping of color string names to their corresponding
            RGB tuple values.
        screen: The primary Pygame display surface.
        clock: The internal clock used to cap the frame rate.
        running: Flag indicating whether the main event loop is active.
        graph: The operational network topology containing zones and edges.
        width: The current width of the Pygame window in pixels.
        height: The current height of the Pygame window in pixels.
        zones: A flattened list of all graph zones.
        pan_x: The current horizontal camera offset in pixels.
        pan_y: The current vertical camera offset in pixels.
        zoom: The current camera zoom multiplier.
        is_panning: Flag tracking if the user is currently in panning mode.
        scale_x: The internal base scaling factor for the X-axis.
        scale_y: The internal base scaling factor for the Y-axis.
        offset_x: The internal base centering offset for the X-axis.
        offset_y: The internal base centering offset for the Y-axis.
        base_radius: The calculated base radius for drawing zone circles.
    """
    COLORS = {
        "green": (0, 128, 0),
        "orange": (255, 165, 0),
        "blue": (0, 0, 255),
        "red": (255, 0, 0),
        "cyan": (0, 255, 255),
        "yellow": (255, 255, 0),
        "purple": (128, 0, 128),
        "brown": (165, 42, 42),
        "lime": (0, 255, 0),
        "magenta": (255, 0, 255),
        "gold": (255, 215, 0),
        "black": (0, 0, 0),
        "maroon": (128, 0, 0),
        "darkred": (139, 0, 0),
        "violet": (238, 130, 238),
        "crimson": (220, 20, 60),
        "indigo": (75, 0, 130),
        "default": (149, 165, 166),
    }

    def __init__(self, graph: Graph, width: int = 800, height: int = 600):
        """Initializes Pygame display and calculates initial camera boundaries.

        Configures a resizable display window, extracts all distinct zones from
        the provided graph, and computes the optimal initial scale, zoom, and
        pan to ensure the graph is centered and reasonably sized upon launch.

        Args:
            graph: The parsed network topology mapping all simulation nodes.
            width: The initial window width in pixels. Defaults to 800.
            height: The initial window height in pixels. Defaults to 600.
        """
        pygame.init()
        self.screen = pygame.display.set_mode(
            (width, height), pygame.RESIZABLE
        )
        pygame.display.set_caption("Fly-in")
        self.clock = pygame.time.Clock()
        self.running = True
        self.graph = graph
        self.width = width
        self.height = height
        self.zones = self.graph.zones.values()
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self.is_panning = False
        (
            self.scale_x, self.scale_y,
            self.offset_x, self.offset_y,
            self.base_radius
        ) = self._calculate_scale_factors()

    def _calculate_scale_factors(
        self
    ) -> tuple[float, float, float, float, int]:
        if not self.graph.zones:
            return 1.0, 1.0, self.width / 2, self.height / 2, 5
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        for zone in self.zones:
            x, y = self.graph.get_coords(zone)
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y
        graph_width = max_x - min_x
        graph_height = max_y - min_y
        inner_width = self.width * 0.8
        inner_height = self.height * 0.8
        inf = float('inf')
        scale_x = inner_width / graph_width if graph_width > 0 else inf
        scale_y = inner_height / graph_height if graph_height > 0 else inf
        scale = min(scale_x, scale_y)
        if scale == inf:
            scale = 1.0
        base_radius = max(5, int(scale * 0.2))
        logical_center_x = min_x + (graph_width / 2)
        logical_center_y = min_y + (graph_height / 2)
        screen_center_x = self.width / 2
        screen_center_y = self.height / 2
        offset_x = screen_center_x - (logical_center_x * scale)
        offset_y = screen_center_y - (-logical_center_y * scale)
        if graph_width > 10:
            self.zoom = graph_width / 10.0
            start_x, start_y = self.graph.get_coords(self.graph.start_zone)
            base_sx = start_x * scale + offset_x
            base_sy = start_y * scale + offset_y
            target_x = self.width * 0.1
            target_y = self.height / 2
            self.pan_x = target_x - (
                (base_sx - screen_center_x) * self.zoom + screen_center_x
            )
            self.pan_y = target_y - (
                (base_sy - screen_center_y) * self.zoom + screen_center_y
            )
        else:
            self.zoom = 1.0
            self.pan_x = 0.0
            self.pan_y = 0.0
        return scale, scale, offset_x, offset_y, base_radius

    def _transform_coords(self, x: float, y: float) -> tuple[int, int]:
        """Converts logical grid coordinates to physical pixel coordinates."""
        base_x = x * self.scale_x + self.offset_x
        base_y = -y * self.scale_y + self.offset_y
        cx, cy = self.width / 2, self.height / 2
        screen_x = int((base_x - cx) * self.zoom + cx + self.pan_x)
        screen_y = int((base_y - cy) * self.zoom + cy + self.pan_y)
        return screen_x, screen_y

    def _draw_connections(self) -> None:
        """Draws lines between connected zones."""
        line_color = (255, 255, 255)  # White
        line_width = 2
        spacing = 6 * self.zoom
        for edge in self.graph.edges:
            z1 = self.graph.zones.get(edge.zone1)
            z2 = self.graph.zones.get(edge.zone2)
            if z1 and z2:
                start_x, start_y = self.graph.get_coords(z1)
                end_x, end_y = self.graph.get_coords(z2)
                sx1, sy1 = self._transform_coords(start_x, start_y)
                sx2, sy2 = self._transform_coords(end_x, end_y)
                capacity = edge.capacity
                dx = sx2 - sx1
                dy = sy2 - sy1
                length = math.hypot(dx, dy)
                if length == 0:
                    continue
                # Calculate the perpendicular (normal) unit vector
                nx = -dy / length
                ny = dx / length
                for i in range(capacity):
                    offset_multiplier = i - ((capacity - 1) / 2.0)
                    total_offset = offset_multiplier * spacing
                    off_sx1 = sx1 + (nx * total_offset)
                    off_sy1 = sy1 + (ny * total_offset)
                    off_sx2 = sx2 + (nx * total_offset)
                    off_sy2 = sy2 + (ny * total_offset)
                    pygame.draw.line(
                        self.screen, line_color, (int(off_sx1), int(off_sy1)),
                        (int(off_sx2), int(off_sy2)), line_width
                    )

    def _draw_rainbow_wheel(
        self, screen_pos: tuple[int, int], radius: float
    ) -> None:
        """Draws the rainbow wheel using the dynamically provided radius."""
        rainbow_colors = [
            self.COLORS["red"],
            self.COLORS["orange"],
            self.COLORS["yellow"],
            self.COLORS["green"],
            self.COLORS["blue"],
            self.COLORS["indigo"],
            self.COLORS["violet"],
        ]
        step = radius / len(rainbow_colors)
        for color in rainbow_colors:
            pygame.draw.circle(self.screen, color, screen_pos, int(radius))
            radius -= step

    def _draw_zones(self) -> None:
        """Draws circles representing the zones over the connections."""
        base_zoomed_radius = max(5, int(self.base_radius * self.zoom))
        white = (255, 255, 255)
        for zone in self.zones:
            x, y = self.graph.get_coords(zone)
            screen_pos = self._transform_coords(x, y)
            capacity = zone.capacity
            if capacity == sys.maxsize or capacity == float('inf'):
                capacity = self.graph.nb_drones
            multiplier = min(math.sqrt(capacity), 3.0)
            radius = base_zoomed_radius * multiplier
            color_name = zone.color
            default = self.COLORS["default"]
            if color_name is None:
                pygame.draw.circle(
                    self.screen, default, screen_pos, int(radius)
                )
            elif color_name.lower() == "rainbow":
                self._draw_rainbow_wheel(screen_pos, radius)
            else:
                color = self.COLORS.get(color_name.lower(), default)
                pygame.draw.circle(self.screen, color, screen_pos, int(radius))
            pygame.draw.circle(self.screen, white, screen_pos, int(radius), 2)

    def _get_drone_state_info(
        self, state: dict[str, Zone | Connection]
    ) -> dict[str, tuple[int, int]]:
        """Group drones by location to assign lane/slot indices."""
        groups: dict[str, list[str]] = {}
        for d_id, loc in state.items():
            loc_key = loc.name
            if loc_key not in groups:
                groups[loc_key] = []
            groups[loc_key].append(d_id)
        drone_info = {}
        for loc_key, d_ids in groups.items():
            d_ids.sort(key=lambda d_id: int(d_id.replace("D", "")))
            count = len(d_ids)
            for index, d_id in enumerate(d_ids):
                drone_info[d_id] = (index, count)
        return drone_info

    def _get_drone_screen_pos(
        self, location, index: int, count: int
    ) -> pygame.math.Vector2:
        """Calculate exact screen coordinates for lanes and clusters."""
        logical_x, logical_y = self.graph.get_coords(location)
        sx = float(self._transform_coords(logical_x, logical_y)[0])
        sy = float(self._transform_coords(logical_x, logical_y)[1])
        if isinstance(location, Zone):
            # Spread drones in a circular pattern if there is more than one
            if count > 1:
                angle = (2 * math.pi / count) * index
                capacity = location.capacity
                if capacity == sys.maxsize or capacity == float('inf'):
                    capacity = self.graph.nb_drones
                multiplier = min(math.sqrt(capacity), 3.0)
                inner_radius = self.base_radius * self.zoom * multiplier * 0.6
                spread_radius = max(4, int(inner_radius))
                sx += math.cos(angle) * spread_radius
                sy += math.sin(angle) * spread_radius
        elif isinstance(location, Connection):
            # Calculate lane offsets (identical to _draw_connections logic)
            z1 = self.graph.zones.get(location.zone1)
            z2 = self.graph.zones.get(location.zone2)
            if z1 and z2:
                x1, y1 = self.graph.get_coords(z1)
                x2, y2 = self.graph.get_coords(z2)
                sx1, sy1 = self._transform_coords(x1, y1)
                sx2, sy2 = self._transform_coords(x2, y2)
                dx = sx2 - sx1
                dy = sy2 - sy1
                length = math.hypot(dx, dy)
                if length > 0:
                    nx = -dy / length
                    ny = dx / length
                    capacity = location.capacity
                    if capacity == sys.maxsize or capacity <= 0:
                        capacity = 1
                    spacing = 6 * self.zoom
                    offset_multiplier = index - ((capacity - 1) / 2.0)
                    sx += nx * offset_multiplier * spacing
                    sy += ny * offset_multiplier * spacing
        return pygame.math.Vector2(sx, sy)

    def _draw_drones(
        self,
        drones: list[Drone],
        history: list[dict[str, Zone | Connection]],
        turn: int,
        progress: float
    ) -> None:
        """Draws drones interpolating between current turn and next turn."""
        drone_radius = max(3, int(self.base_radius * self.zoom * 0.4))
        current_state = history[turn]
        next_state = history[min(turn + 1, len(history) - 1)]
        current_info = self._get_drone_state_info(current_state)
        next_info = self._get_drone_state_info(next_state)
        for drone in drones:
            start_loc = current_state[drone.id]
            end_loc = next_state[drone.id]
            start_idx, start_count = current_info[drone.id]
            end_idx, end_count = next_info[drone.id]
            start_pos = self._get_drone_screen_pos(
                start_loc, start_idx, start_count
            )
            end_pos = self._get_drone_screen_pos(end_loc, end_idx, end_count)
            current_pos = start_pos.lerp(end_pos, progress)
            screen_pos = (int(current_pos.x), int(current_pos.y))
            color = self.COLORS["cyan"]
            pygame.draw.circle(self.screen, color, screen_pos, drone_radius)

    def render(
        self, drones: list[Drone], history: list[dict[str, Zone | Connection]]
    ) -> None:
        """Executes main Pygame event loop and continuously redraws the frame.

        Maintains a 60 FPS update cycle. Intercepts and processes OS window
        events, keyboard interaction and mouse inputs for manipulating the
        interactive camera (panning and zooming). Clears the screen
        and redraws all edges and zones on every tick.
        """
        tick_progress = 0.0
        current_turn = 0
        animation_speed = 0.05
        max_turn = len(history) - 1
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.width = event.w
                    self.height = event.h
                    (
                        self.scale_x, self.scale_y,
                        self.offset_x, self.offset_y,
                        self.base_radius
                    ) = self._calculate_scale_factors()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        self.running = False
                # --- CAMERA CONTROLS ---
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.is_panning = True
                        pygame.mouse.get_rel()  # Flush old relative movement
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.is_panning = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.is_panning:
                        # Add relative mouse movement to pan offset
                        self.pan_x += event.rel[0]
                        self.pan_y += event.rel[1]
                elif event.type == pygame.MOUSEWHEEL:
                    mx, my = pygame.mouse.get_pos()
                    cx, cy = self.width / 2, self.height / 2
                    old_zoom = self.zoom
                    zoom_factor = 1.15 if event.y > 0 else (1 / 1.15)
                    self.zoom *= zoom_factor
                    # Clamp zoom to prevent flipping or freezing
                    self.zoom = max(0.5, min(self.zoom, 15.0))
                    # Adjust panning so the zoom centers on the mouse cursor
                    ratio = self.zoom / old_zoom
                    self.pan_x = mx - cx - (mx - cx - self.pan_x) * ratio
                    self.pan_y = my - cy - (my - cy - self.pan_y) * ratio
            if current_turn < max_turn:
                tick_progress += animation_speed
                if tick_progress >= 1.0:
                    current_turn += 1
                    tick_progress = 0.0
            else:
                tick_progress = 0.0  # Reached the end, stop animating
            self.screen.fill(color=(30, 30, 30))
            self._draw_connections()
            self._draw_zones()
            self._draw_drones(drones, history, current_turn, tick_progress)
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
