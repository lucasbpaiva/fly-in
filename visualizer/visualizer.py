import pygame
from graph import Graph


class Visualizer:
    """
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
        """
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
        (  # Calculate these once during initialization
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
        offset_y = screen_center_y - (logical_center_y * scale)
        return scale, scale, offset_x, offset_y, base_radius

    def _transform_coords(self, x: float, y: float) -> tuple[int, int]:
        """Converts logical grid coordinates to physical pixel coordinates."""
        screen_x = int(x * self.scale_x + self.offset_x)
        screen_y = int(y * self.scale_y + self.offset_y)
        return screen_x, screen_y

    def _draw_connections(self) -> None:
        """Draws lines between connected zones."""
        line_color = (255, 255, 255)  # White
        line_width = 3
        for edge in self.graph.edges:
            z1 = self.graph.zones.get(edge.zone1)
            z2 = self.graph.zones.get(edge.zone2)
            if z1 and z2:
                start_x, start_y = self.graph.get_coords(z1)
                end_x, end_y = self.graph.get_coords(z2)
                start_pos = self._transform_coords(start_x, start_y)
                end_pos = self._transform_coords(end_x, end_y)
                pygame.draw.line(
                    self.screen, line_color, start_pos, end_pos, line_width
                )

    def _draw_rainbow_wheel(self, screen_pos: tuple[int, int]) -> None:
        """
        """
        rainbow_colors = [
            self.COLORS["red"],
            self.COLORS["orange"],
            self.COLORS["yellow"],
            self.COLORS["green"],
            self.COLORS["blue"],
            self.COLORS["indigo"],
            self.COLORS["violet"],
        ]
        radius = float(self.base_radius)
        step = radius / len(rainbow_colors)
        for color in rainbow_colors:
            pygame.draw.circle(self.screen, color, screen_pos, int(radius))
            radius -= step

    def _draw_zones(self) -> None:
        """Draws circles representing the zones over the connections."""
        radius = self.base_radius
        for zone in self.zones:
            x, y = self.graph.get_coords(zone)
            screen_pos = self._transform_coords(x, y)
            color_name = zone.color
            default = self.COLORS["default"]
            if color_name is None:
                pygame.draw.circle(self.screen, default, screen_pos, radius)
                return
            if color_name.lower() == "rainbow":
                self._draw_rainbow_wheel(screen_pos)
                return
            rgb_color = self.COLORS.get(color_name.lower(), default)
            pygame.draw.circle(self.screen, rgb_color, screen_pos, radius)

    def render(self) -> None:
        """
        """
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
            self.screen.fill(color=(30, 30, 30))
            self._draw_connections()
            self._draw_zones()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
