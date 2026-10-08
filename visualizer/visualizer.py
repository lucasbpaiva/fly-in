import pygame
from graph import Graph


class Visualizer:
    """
    """
    COLORS = {
        "green": (46, 204, 113),
        "orange": (230, 126, 34),
        "blue": (52, 152, 219),
        "red": (231, 76, 60),
        "cyan": (0, 255, 255),
        "yellow": (241, 196, 15),
        "default": (149, 165, 166)
    }

    def __init__(self, graph: Graph, width: int = 800, height: int = 600):
        """
        """
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Fly-in")
        self.clock = pygame.time.Clock()
        self.running = True
        self.graph = graph
        self.width = width
        self.height = height
        (  # Calculate these once during initialization
            self.scale_x, self.scale_y, self.offset_x, self.offset_y
        ) = self._calculate_scale_factors()

    def _calculate_scale_factors(self) -> tuple[float, float, float, float]:
        if not self.graph.zones:
            return 1.0, 1.0, self.width / 2, self.height / 2
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        for zone in self.graph.zones.values():
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
        logical_center_x = min_x + (graph_width / 2)
        logical_center_y = min_y + (graph_height / 2)
        screen_center_x = self.width / 2
        screen_center_y = self.height / 2
        offset_x = screen_center_x - (logical_center_x * scale)
        offset_y = screen_center_y - (logical_center_y * scale)
        return scale, scale, offset_x, offset_y

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

    def _draw_zones(self) -> None:
        # Implementation using pygame.draw.circle
        pass

    def render(self) -> None:
        """
        """
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            self.screen.fill(color=(30, 30, 30))
            self._draw_connections()
            self._draw_zones()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
