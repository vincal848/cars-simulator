"""Pan and zoom over a longitude/latitude map that wraps horizontally.

The camera works in the window's physical pixels. Its zoom range is set from the
viewport, so a larger window shows the same view in more detail rather than a
smaller continent. The camera is presentation only; the simulation never sees
screen coordinates.
"""

import math

import pygame

# Latitude extent of the Americas theatre, with a small ocean margin.
NORTH_LIMIT = 81
SOUTH_LIMIT = -62
# The point of the map at the centre of the world view.
HOME = (-82, 21)
# At world view the continent fills this share of the viewport height.
WORLD_FILL = 0.85
MAX_ZOOM = 5.5  # Closest zoom, as a multiple of the world view.
DEFAULT_VIEWPORT = pygame.Rect(0, 0, 1200, 742)


class Camera:
    def __init__(self, viewport: pygame.Rect = DEFAULT_VIEWPORT) -> None:
        self.viewport = pygame.Rect(viewport)
        self.scale = self.min_scale
        self.offset = [0.0, 0.0]
        self.home()

    @property
    def min_scale(self) -> float:
        """Pixels per degree at world view."""
        return self.viewport.height * WORLD_FILL / (NORTH_LIMIT - SOUTH_LIMIT)

    @property
    def zoom_level(self) -> float:
        """How far in the camera is: 1 at world view, up to MAX_ZOOM."""
        return self.scale / self.min_scale

    @property
    def period(self) -> float:
        """Screen width of 360 degrees of longitude."""
        return 360 * self.scale

    def home(self) -> None:
        """Show the whole theatre."""
        self.scale = self.min_scale
        center = self.viewport.center
        self.offset = [center[0] - HOME[0] * self.scale, center[1] + HOME[1] * self.scale]
        self.constrain()

    def resize(self, viewport: pygame.Rect) -> None:
        """Adapt to a new window size, keeping the same part of the map in the middle and
        the same relative zoom."""
        center = self.to_world(self.viewport.center)
        level = self.zoom_level
        self.viewport = pygame.Rect(viewport)
        self.scale = self.min_scale * level
        self.offset = [
            self.viewport.centerx - center[0] * self.scale,
            self.viewport.centery + center[1] * self.scale,
        ]
        self.constrain()

    def constrain(self) -> None:
        center_x = self.viewport.centerx
        self.offset[0] = center_x + (self.offset[0] - center_x) % self.period
        low = self.viewport.bottom + SOUTH_LIMIT * self.scale
        high = self.viewport.top + NORTH_LIMIT * self.scale
        # When the whole map fits on screen, keep it centred vertically.
        self.offset[1] = max(low, min(high, self.offset[1])) if low <= high else (low + high) / 2

    def copies(self, point: tuple[float, float], margin: int = 60) -> list[tuple[float, float]]:
        """Every horizontally wrapped copy of ``point`` near the viewport."""
        x, y = point
        left, right = self.viewport.left - margin, self.viewport.right + margin
        first = math.floor((left - x) / self.period)
        last = math.ceil((right - x) / self.period)
        return [
            (x + k * self.period, y) for k in range(first, last + 1) if left <= x + k * self.period <= right
        ]

    def nearest(self, point: tuple[float, float]) -> tuple[float, float]:
        """The wrapped copy of ``point`` closest to the centre of the viewport."""
        x, y = point
        return x + round((self.viewport.centerx - x) / self.period) * self.period, y

    def project(self, coordinate: tuple[float, float]) -> tuple[int, int]:
        longitude, latitude = coordinate
        return int(self.offset[0] + longitude * self.scale), int(self.offset[1] - latitude * self.scale)

    def to_world(self, point: tuple[float, float]) -> tuple[float, float]:
        """The longitude and latitude under a screen point (longitude not wrapped)."""
        return (point[0] - self.offset[0]) / self.scale, (self.offset[1] - point[1]) / self.scale

    def zoom(self, factor: float, point: tuple[float, float]) -> None:
        """Zoom by ``factor`` keeping ``point`` fixed on screen."""
        new_scale = min(self.min_scale * MAX_ZOOM, max(self.min_scale, self.scale * factor))
        ratio = new_scale / self.scale
        self.offset = [point[i] + (self.offset[i] - point[i]) * ratio for i in range(2)]
        self.scale = new_scale
        self.constrain()

    def pan(self, dx: float, dy: float) -> None:
        self.offset[0] += dx
        self.offset[1] += dy
        self.constrain()


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    """Even-odd ray casting test."""
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if (a[1] > y) != (b[1] > y):
            crossing = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < crossing:
                inside = not inside
    return inside
