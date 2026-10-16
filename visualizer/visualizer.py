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
        "silver": (192, 192, 192),
        "hotpink": (255, 105, 180),
        "black": (0, 0, 0),
        "maroon": (128, 0, 0),
        "gray": (128, 128, 128),
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
        base_radius = max(5, int(scale * 0.15))
        logical_center_x = min_x + (graph_width / 2)
        logical_center_y = min_y + (graph_height / 2)
        screen_center_x = self.width / 2
        screen_center_y = self.height / 2
        offset_x = screen_center_x - (logical_center_x * scale)
        offset_y = screen_center_y - (-logical_center_y * scale)
        if graph_width > 6:
            self.zoom = graph_width / 6.0
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
        spacing = 8 * self.zoom
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
        label_font_size = max(14, int(base_zoomed_radius * 1.2))
        label_font = pygame.font.Font(size=label_font_size)
        cap_font_size = max(12, base_zoomed_radius)
        cap_font = pygame.font.Font(size=cap_font_size)
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
            if zone.type == "blocked":
                offset = int(radius * math.sin(math.pi / 4))
                cx, cy = screen_pos
                line_width = max(2, int(3 * self.zoom))
                pygame.draw.line(
                    self.screen, white,
                    (cx - offset, cy - offset), (cx + offset, cy + offset),
                    line_width
                )
                pygame.draw.line(
                    self.screen, white,
                    (cx - offset, cy + offset), (cx + offset, cy - offset),
                    line_width
                )
                pygame.draw.circle(
                    self.screen, self.COLORS["red"],
                    screen_pos, int(radius) + 6, 3
                )
            if zone.type == "restricted":
                yellow = self.COLORS["yellow"]
                pygame.draw.circle(
                    self.screen, yellow, screen_pos, int(radius) + 6, 3
                )
            if zone.type == "priority":
                lime = self.COLORS["lime"]
                pygame.draw.circle(
                    self.screen, lime, screen_pos, int(radius) + 6, 3
                )
            cap_text = f"cap: {capacity}"
            cap_surface = cap_font.render(cap_text, True, (200, 200, 200))
            cap_y = screen_pos[1] + int(radius + 12)
            cap_rect = cap_surface.get_rect(center=(screen_pos[0], cap_y))
            self.screen.blit(cap_surface, cap_rect)
            if zone.is_start or zone.is_end:
                text = "START" if zone.is_start else "END"
                text_surface = label_font.render(text, True, white)
                ty = screen_pos[1] - int(radius + 14)
                text_rect = text_surface.get_rect(center=(screen_pos[0], ty))
                self.screen.blit(text_surface, text_rect)

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

    def _lane_point(
        self, edge: Connection, lane: int, zone_name: str
    ) -> pygame.math.Vector2:
        """Screen point where a given lane touches the given end of an edge.

        Uses the same normal/spacing math as _draw_connections so that drones
        sit exactly on the drawn lines.
        """
        z1 = self.graph.zones[edge.zone1]
        z2 = self.graph.zones[edge.zone2]
        p1 = pygame.math.Vector2(
            self._transform_coords(*self.graph.get_coords(z1))
        )
        p2 = pygame.math.Vector2(
            self._transform_coords(*self.graph.get_coords(z2))
        )
        base = p1 if zone_name == edge.zone1 else p2
        d = p2 - p1
        length = d.length()
        if length == 0:
            return base
        normal = pygame.math.Vector2(-d.y, d.x) / length
        capacity = edge.capacity
        if capacity == sys.maxsize or capacity <= 0:
            capacity = 1
        offset = (lane - (capacity - 1) / 2.0) * 6 * self.zoom
        return base + normal * offset

    def _get_transit_lanes(
        self,
        current_state: dict[str, Zone | Connection],
        next_state: dict[str, Zone | Connection],
    ) -> dict[str, int]:
        """Assign lanes to drones that hop directly zone -> zone this turn."""
        groups: dict[tuple[str, str], list[str]] = {}
        for d_id, start in current_state.items():
            end = next_state[d_id]
            if (
                isinstance(start, Zone) and isinstance(end, Zone)
                and start.name != end.name
            ):
                key = (min(start.name, end.name), max(start.name, end.name))
                groups.setdefault(key, []).append(d_id)
        lanes: dict[str, int] = {}
        for ids in groups.values():
            ids.sort(key=lambda d: int(d.replace("D", "")))
            for i, d_id in enumerate(ids):
                lanes[d_id] = i
        return lanes

    def _build_drone_path(
        self,
        start_loc: Zone | Connection,
        end_loc: Zone | Connection,
        start_pos: pygame.math.Vector2,
        end_pos: pygame.math.Vector2,
        start_idx: int,
        end_idx: int,
        transit_lane: int,
    ) -> list[pygame.math.Vector2]:
        """Waypoints a drone follows during one turn, routed through lanes."""
        path = [start_pos]
        if isinstance(start_loc, Zone) and isinstance(end_loc, Zone):
            if start_loc.name != end_loc.name:
                edge = self.graph.get_connection(start_loc.name, end_loc.name)
                if edge is not None:
                    path.append(
                        self._lane_point(edge, transit_lane, start_loc.name)
                    )
                    path.append(
                        self._lane_point(edge, transit_lane, end_loc.name)
                    )
        elif isinstance(start_loc, Zone) and isinstance(end_loc, Connection):
            # Leaving a zone onto a lane
            path.append(self._lane_point(end_loc, end_idx, start_loc.name))
        elif isinstance(start_loc, Connection) and isinstance(end_loc, Zone):
            # Arriving at a zone from a lane
            path.append(self._lane_point(start_loc, start_idx, end_loc.name))
        path.append(end_pos)
        return path

    @staticmethod
    def _point_along(
        path: list[pygame.math.Vector2], t: float
    ) -> pygame.math.Vector2:
        """Point at fraction t of the total length of a polyline."""
        segments = list(zip(path, path[1:]))
        lengths = [a.distance_to(b) for a, b in segments]
        total = sum(lengths)
        if total == 0:
            return path[-1]
        target = t * total
        for (a, b), length in zip(segments, lengths):
            if length > 0 and target <= length:
                return a.lerp(b, target / length)
            target -= length
        return path[-1]

    def _get_drone_screen_pos(
        self, location: Zone | Connection, index: int, count: int
    ) -> pygame.math.Vector2:
        """Calculate exact screen coordinates for lanes and clusters."""
        logical_x, logical_y = self.graph.get_coords(location)
        sx, sy = map(float, self._transform_coords(logical_x, logical_y))
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
            return pygame.math.Vector2(sx, sy)
        elif isinstance(location, Connection):
            a = self._lane_point(location, index, location.zone1)
            b = self._lane_point(location, index, location.zone2)
            return (a + b) / 2

    def _draw_drones(
        self,
        drones: list[Drone],
        history: list[dict[str, Zone | Connection]],
        turn: int,
        progress: float
    ) -> None:
        """Draws drones interpolating between current turn and next turn."""
        r = max(3, int(self.base_radius * self.zoom * 0.9))
        font_size = max(10, int(r * 1.2))
        font = pygame.font.Font(None, font_size)
        current_state = history[turn]
        next_state = history[min(turn + 1, len(history) - 1)]
        current_info = self._get_drone_state_info(current_state)
        next_info = self._get_drone_state_info(next_state)
        transit_lanes = self._get_transit_lanes(current_state, next_state)
        for drone in drones:
            start_loc = current_state[drone.id]
            end_loc = next_state[drone.id]
            start_idx, start_count = current_info[drone.id]
            end_idx, end_count = next_info[drone.id]
            start_pos = self._get_drone_screen_pos(
                start_loc, start_idx, start_count
            )
            end_pos = self._get_drone_screen_pos(end_loc, end_idx, end_count)
            path = self._build_drone_path(
                start_loc, end_loc, start_pos, end_pos,
                start_idx, end_idx, transit_lanes.get(drone.id, 0)
            )
            current_pos = self._point_along(path, progress)
            x, y = (int(current_pos.x), int(current_pos.y))
            color = self.COLORS["hotpink"]
            vertices = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
            pygame.draw.polygon(self.screen, color, vertices)
            pygame.draw.polygon(self.screen, (255, 255, 255), vertices, 2)
            try:
                drone_num = int(drone.id.replace("D", ""))
                label = f"{drone_num:02d}"
            except ValueError:
                label = drone.id[:2]
            black = self.COLORS["black"]
            text_surface = font.render(text=label, antialias=True, color=black)
            text_rect = text_surface.get_rect(center=(x, y))
            self.screen.blit(text_surface, text_rect)

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
        animation_speed = 0.033
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
                    # --- REPLAY ANIMATION ---
                    elif event.key == pygame.K_r:
                        current_turn = 0
                        tick_progress = 0.0
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
            self.screen.fill(color=(34, 36, 41))
            self._draw_connections()
            self._draw_zones()
            self._draw_drones(drones, history, current_turn, tick_progress)
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
