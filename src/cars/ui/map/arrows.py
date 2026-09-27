"""Travel arrows: a smooth, tapering ribbon through the route with a broad head.

The route is smoothed with a Catmull-Rom spline through the province anchors, so
it bends naturally instead of zig-zagging, and is drawn with a dark outline so it
reads on any terrain or nation colour.
"""

import math
from itertools import pairwise

import pygame

OUTLINE = (24, 22, 20)
SAMPLES_PER_STEP = 10
Point = tuple[float, float]


def draw_route(
    surface: pygame.Surface, points: list[Point], color, scale: float = 1.0, alpha: int = 235
) -> None:
    """Draw an arrow through ``points`` (screen pixels); ``scale`` is the UI scale."""
    if len(points) < 2 or all(math.dist(points[0], p) < 1 for p in points[1:]):
        return
    path = _smooth(points)
    head_length = 15 * scale
    shaft = _trim(path, head_length * 0.7)
    if len(shaft) < 2:
        shaft = [path[0], path[-1]]
    left, right = _ribbon(shaft, 2.2 * scale, 4.2 * scale)
    outline_left, outline_right = _ribbon(shaft, 3.6 * scale, 5.6 * scale)
    tip = path[-1]
    base = shaft[-1]
    angle = math.atan2(tip[1] - base[1], tip[0] - base[0])
    head = _head(tip, angle, head_length, 9 * scale)
    outline_head = _head(_step(tip, angle, 1.6 * scale), angle, head_length + 3 * scale, 11.5 * scale)

    xs = [p[0] for p in outline_left + outline_right + outline_head]
    ys = [p[1] for p in outline_left + outline_right + outline_head]
    box = pygame.Rect(math.floor(min(xs)) - 2, math.floor(min(ys)) - 2, 0, 0)
    box.width = math.ceil(max(xs)) - box.x + 3
    box.height = math.ceil(max(ys)) - box.y + 3
    layer = pygame.Surface(box.size, pygame.SRCALPHA)

    def local(polygon: list[Point]) -> list[Point]:
        return [(x - box.x, y - box.y) for x, y in polygon]

    pygame.draw.polygon(layer, OUTLINE, local(outline_left + outline_right[::-1]))
    pygame.draw.polygon(layer, OUTLINE, local(outline_head))
    pygame.draw.polygon(layer, color, local(left + right[::-1]))
    pygame.draw.polygon(layer, color, local(head))
    # A lighter spine gives the ribbon a little body.
    pygame.draw.lines(layer, _lighten(color), False, local(shaft), max(1, round(scale)))
    layer.set_alpha(alpha)
    surface.blit(layer, box)


def _smooth(points: list[Point]) -> list[Point]:
    """Catmull-Rom spline through every point."""
    if len(points) == 2:
        return list(points)
    padded = [points[0], *points, points[-1]]
    result = [points[0]]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        for step in range(1, SAMPLES_PER_STEP + 1):
            t = step / SAMPLES_PER_STEP
            t2, t3 = t * t, t * t * t
            result.append(
                tuple(
                    0.5
                    * (
                        2 * p1[k]
                        + (-p0[k] + p2[k]) * t
                        + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                        + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3
                    )
                    for k in (0, 1)
                )
            )
    return result


def _trim(path: list[Point], length: float) -> list[Point]:
    """``path`` shortened by ``length`` at its end, to make room for the head."""
    remaining = length
    trimmed = list(path)
    while len(trimmed) > 1:
        a, b = trimmed[-2], trimmed[-1]
        segment = math.dist(a, b)
        if segment > remaining:
            f = (segment - remaining) / segment
            trimmed[-1] = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            return trimmed
        remaining -= segment
        trimmed.pop()
    return trimmed


def _ribbon(path: list[Point], start: float, end: float) -> tuple[list[Point], list[Point]]:
    """The two edges of a band along ``path`` whose half-width grows from ``start`` to ``end``."""
    lengths = [0.0]
    for a, b in pairwise(path):
        lengths.append(lengths[-1] + math.dist(a, b))
    total = lengths[-1] or 1
    left, right = [], []
    for i, (x, y) in enumerate(path):
        before = path[max(0, i - 1)]
        after = path[min(len(path) - 1, i + 1)]
        dx, dy = after[0] - before[0], after[1] - before[1]
        norm = math.hypot(dx, dy) or 1
        nx, ny = -dy / norm, dx / norm
        half = start + (end - start) * lengths[i] / total
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))
    return left, right


def _head(tip: Point, angle: float, length: float, half_width: float) -> list[Point]:
    back = _step(tip, angle, -length)
    nx, ny = -math.sin(angle), math.cos(angle)
    return [
        tip,
        (back[0] + nx * half_width, back[1] + ny * half_width),
        (back[0] - nx * half_width, back[1] - ny * half_width),
    ]


def _step(point: Point, angle: float, distance: float) -> Point:
    return point[0] + math.cos(angle) * distance, point[1] + math.sin(angle) * distance


def _lighten(color) -> tuple[int, int, int]:
    return tuple(min(255, int(c + (255 - c) * 0.45)) for c in color[:3])
