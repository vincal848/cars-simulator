"""Vector heraldry and leaf scrollwork for the Renaissance interface.

Fleurs and crowns are drawn at three times their size and smoothed down, then cached.
"""

import math

import pygame

from cars.ui.palette import GOLD

PALE = (246, 218, 147)
SUPERSAMPLE = 3

_cache: dict[tuple, pygame.Surface] = {}


def _draw_fleur(surface: pygame.Surface, center, size: float = 30, color=GOLD) -> None:
    x, y = center
    k = size / 40

    def polygon(points) -> None:
        pygame.draw.polygon(surface, color, [(x + a * k, y + b * k) for a, b in points])

    polygon([(0, -22), (-7, -11), (-6, -2), (-2, 7), (0, 11), (2, 7), (6, -2), (7, -11)])
    polygon([
        (-2, 8), (-9, 1), (-18, 0), (-22, -7), (-21, -13), (-16, -16), (-11, -14),
        (-9, -9), (-13, -10), (-15, -7), (-12, -4), (-7, -3), (0, 7),
    ])  # fmt: skip
    polygon([
        (2, 8), (9, 1), (18, 0), (22, -7), (21, -13), (16, -16), (11, -14),
        (9, -9), (13, -10), (15, -7), (12, -4), (7, -3), (0, 7),
    ])  # fmt: skip
    polygon([(-9, 6), (9, 6), (9, 10), (-9, 10)])
    polygon([(-3, 11), (-9, 17), (-3, 17), (0, 22), (3, 17), (9, 17), (3, 11)])
    stem = PALE if color == GOLD else color
    pygame.draw.line(surface, stem, (x, y - 17 * k), (x, y + 3 * k), max(1, int(k)))


def _draw_crown(surface: pygame.Surface, center, width: float = 40) -> None:
    x, y = center
    k = width / 40
    points = [(-18, 8), (-21, -9), (-10, -1), (0, -16), (10, -1), (21, -9), (18, 8)]
    pygame.draw.polygon(surface, GOLD, [(x + a * k, y + b * k) for a, b in points])
    pygame.draw.line(surface, PALE, (x - 17 * k, y + 5 * k), (x + 17 * k, y + 5 * k), 2)
    for dx, dy in [(-21, -9), (0, -16), (21, -9)]:
        pygame.draw.circle(surface, PALE, (int(x + dx * k), int(y + dy * k)), 2)


def _supersampled(key: tuple, size: float, draw) -> pygame.Surface:
    if key not in _cache:
        extent = int(size * 1.5 + 8)
        canvas = pygame.Surface((extent * SUPERSAMPLE, extent * SUPERSAMPLE), pygame.SRCALPHA)
        draw(canvas, (extent * 1.5, extent * 1.5), size * SUPERSAMPLE)
        _cache[key] = pygame.transform.smoothscale(canvas, (extent, extent))
    return _cache[key]


def _blit_centered(surface: pygame.Surface, icon: pygame.Surface, center) -> None:
    surface.blit(icon, (center[0] - icon.get_width() / 2, center[1] - icon.get_height() / 2))


def fleur(surface: pygame.Surface, center, size: float = 30, color=GOLD) -> None:
    icon = _supersampled(("fleur", size, color), size, lambda canvas, c, s: _draw_fleur(canvas, c, s, color))
    _blit_centered(surface, icon, center)


def crown(surface: pygame.Surface, center, width: float = 40) -> None:
    _blit_centered(surface, _supersampled(("crown", width), width, _draw_crown), center)


def branch(surface: pygame.Surface, start, direction: int = 1, length: float = 75, color=GOLD) -> None:
    """A curved stem with alternating pointed leaves."""
    x, y = start

    def point(t: float) -> tuple[float, float]:
        return x + direction * length * t, y - 10 * math.sin(t * math.pi)

    pygame.draw.lines(surface, color, False, [point(i / 24) for i in range(25)], 1)
    for i in range(1, 8):
        px, py = point(i / 9)
        sign = -1 if i % 2 else 1
        base = (px - 3 * direction, py)
        tip = (px + 11 * direction, py + sign * 11)
        leaf = []
        for bulge, steps in [(4, range(13)), (-4, range(12, -1, -1))]:
            for step in steps:
                t = step / 12
                curve = math.sin(t * math.pi) * bulge
                leaf.append(
                    (
                        base[0] + (tip[0] - base[0]) * t + curve * direction,
                        base[1] + (tip[1] - base[1]) * t - curve * sign,
                    )
                )
        pygame.draw.polygon(surface, color, leaf)
