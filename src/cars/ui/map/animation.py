"""Marching a unit along its route after a move order. Cosmetic: the move has already resolved."""

import math

STEP_SECONDS = 0.32
ARRIVAL_SECONDS = 0.55

Point = tuple[float, float]


class MoveAnimation:
    def __init__(self, unit_id: str, route: list[str], start: Point) -> None:
        self.unit = unit_id
        self.route = route
        self.elapsed = 0.0
        self.position = start

    @property
    def segment(self) -> int:
        return min(int(self.elapsed / STEP_SECONDS), len(self.route) - 1)

    @property
    def arrived(self) -> bool:
        return int(self.elapsed / STEP_SECONDS) >= len(self.route) - 1

    @property
    def arrival_radius(self) -> int:
        """Radius of the ring that pulses around the destination."""
        return 12 + int((self.elapsed - self.segment * STEP_SECONDS) * 35)

    def bob(self) -> float:
        return math.sin(self.elapsed * 28) * 2

    def update(self, dt: float, anchors: dict[str, Point], period: float) -> bool:
        """Advance the march; returns True once the animation has finished."""
        self.elapsed += dt
        step = int(self.elapsed / STEP_SECONDS)
        if step >= len(self.route) - 1:
            self.position = anchors[self.route[-1]]
            return self.elapsed >= (len(self.route) - 1) * STEP_SECONDS + ARRIVAL_SECONDS
        a, b = anchors[self.route[step]], anchors[self.route[step + 1]]
        # Take the short way round when the route crosses the map's wrap seam.
        b = (b[0] + round((a[0] - b[0]) / period) * period, b[1])
        t = (self.elapsed % STEP_SECONDS) / STEP_SECONDS
        self.position = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        return False
