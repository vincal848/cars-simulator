"""Pan and zoom over a longitude/latitude map that wraps horizontally.

The camera is presentation only; the simulation never sees screen coordinates.
"""

import math

from cars.ui.palette import CANVAS_SIZE, MAP_AREA

MIN_SCALE = 4.4
MAX_SCALE = 24
# Latitude extent of the Americas theatre, with a small ocean margin.
NORTH_LIMIT = 81
SOUTH_LIMIT = -62
HOME_OFFSET = (960, 465)


class Camera:
    def __init__(self) -> None:
        self.scale = MIN_SCALE
        self.offset = list(HOME_OFFSET)
        self.constrain()

    @property
    def period(self) -> float:
        """Screen width of 360 degrees of longitude."""
        return 360 * self.scale

    def constrain(self) -> None:
        center_x = CANVAS_SIZE[0] / 2
        self.offset[0] = center_x + (self.offset[0] - center_x) % self.period
        low = MAP_AREA.height + SOUTH_LIMIT * self.scale
        high = NORTH_LIMIT * self.scale
        # When the whole map fits on screen, keep it centred vertically.
        self.offset[1] = max(low, min(high, self.offset[1])) if low <= high else (low + high) / 2

    def copies(self, point: tuple[float, float]) -> list[tuple[float, float]]:
        """Every horizontally wrapped copy of ``point`` near the visible canvas."""
        x, y = point
        margin = 60
        first = math.floor((-margin - x) / self.period)
        last = math.ceil((CANVAS_SIZE[0] + margin - x) / self.period)
        return [
            (x + k * self.period, y)
            for k in range(first, last + 1)
            if -margin <= x + k * self.period <= CANVAS_SIZE[0] + margin
        ]

    def nearest(self, point: tuple[float, float]) -> tuple[float, float]:
        """The wrapped copy of ``point`` closest to the centre of the screen."""
        x, y = point
        return x + round((CANVAS_SIZE[0] / 2 - x) / self.period) * self.period, y

    def project(self, coordinate: tuple[float, float]) -> tuple[int, int]:
        longitude, latitude = coordinate
        return int(self.offset[0] + longitude * self.scale), int(self.offset[1] - latitude * self.scale)

    def zoom(self, factor: float, point: tuple[float, float]) -> None:
        """Zoom by ``factor`` keeping ``point`` fixed on screen."""
        new_scale = min(MAX_SCALE, max(MIN_SCALE, self.scale * factor))
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
