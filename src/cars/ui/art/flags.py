"""National flags, drawn from the simple specifications in ``common/nations.json``.

A specification combines a few parts, painted in this order:

- ``field``: one colour for the whole flag;
- ``stripes``: ``{"direction": "horizontal" | "vertical", "colors": [...]}`` of equal width;
- ``union``: true for the Union Flag over the whole field;
- ``rhombus``: ``{"color": ..., "disc": ...}``, a lozenge with a disc at its centre;
- ``canton``: ``{"color": ..., "stars": n}``, a starred corner at the hoist;
- ``emblem``: ``{"kind": "star" | "stars3" | "sun" | "eagle", "color": ...}`` at the centre.
"""

import math

import pygame

RATIO = 2 / 3  # height to width
SUPERSAMPLE = 3
WHITE = (255, 255, 255)
UNION_BLUE, UNION_RED = (1, 33, 105), (200, 16, 46)
Point = tuple[float, float]


_cache: dict[tuple[str, int], pygame.Surface] = {}


def flag(spec: dict, width: int) -> pygame.Surface:
    """The flag ``spec`` at ``width`` pixels, with a hairline edge."""
    key = repr(sorted(spec.items()))
    if (key, width) not in _cache:
        big = (width * SUPERSAMPLE, round(width * RATIO) * SUPERSAMPLE)
        surface = pygame.Surface(big)
        surface.fill(tuple(spec.get("field", WHITE)))
        if "stripes" in spec:
            _stripes(surface, spec["stripes"])
        if spec.get("union"):
            _union(surface)
        if "rhombus" in spec:
            _rhombus(surface, spec["rhombus"])
        if "canton" in spec:
            _canton(surface, spec["canton"])
        if "emblem" in spec:
            _emblem(surface, spec["emblem"])
        small = pygame.transform.smoothscale(surface, (width, round(width * RATIO)))
        pygame.draw.rect(small, (30, 34, 40), small.get_rect(), 1)
        _cache[(key, width)] = small
    return _cache[(key, width)]


def _stripes(surface: pygame.Surface, stripes: dict) -> None:
    width, height = surface.get_size()
    colors = stripes["colors"]
    for i, color in enumerate(colors):
        if stripes["direction"] == "vertical":
            left, right = round(width * i / len(colors)), round(width * (i + 1) / len(colors))
            surface.fill(tuple(color), pygame.Rect(left, 0, right - left, height))
        else:
            top, bottom = round(height * i / len(colors)), round(height * (i + 1) / len(colors))
            surface.fill(tuple(color), pygame.Rect(0, top, width, bottom - top))


def _union(surface: pygame.Surface) -> None:
    width, height = surface.get_size()
    surface.fill(UNION_BLUE)
    corners = [((0, 0), (width, height)), ((0, height), (width, 0))]
    for start, end in corners:
        pygame.draw.line(surface, WHITE, start, end, round(height * 0.2))
    for start, end in corners:
        pygame.draw.line(surface, UNION_RED, start, end, round(height * 0.067))
    surface.fill(WHITE, pygame.Rect(0, height * 0.4, width, height * 0.2))
    surface.fill(WHITE, pygame.Rect(width / 2 - height * 0.1, 0, height * 0.2, height))
    surface.fill(UNION_RED, pygame.Rect(0, height * 0.44, width, height * 0.12))
    surface.fill(UNION_RED, pygame.Rect(width / 2 - height * 0.06, 0, height * 0.12, height))


def _rhombus(surface: pygame.Surface, rhombus: dict) -> None:
    width, height = surface.get_size()
    margin_x, margin_y = width * 0.08, height * 0.1
    points = [
        (width / 2, margin_y),
        (width - margin_x, height / 2),
        (width / 2, height - margin_y),
        (margin_x, height / 2),
    ]
    pygame.draw.polygon(surface, tuple(rhombus["color"]), points)
    pygame.draw.circle(surface, tuple(rhombus["disc"]), (width / 2, height / 2), height * 0.22)


def _canton(surface: pygame.Surface, canton: dict) -> None:
    width, height = surface.get_size()
    area = pygame.Rect(0, 0, round(width * 0.4), round(height * 7 / 13))
    surface.fill(tuple(canton["color"]), area)
    count = canton.get("stars", 0)
    columns = max(1, round(math.sqrt(count * area.width / area.height))) if count else 0
    rows = math.ceil(count / columns) if columns else 0
    for i in range(count):
        column, row = i % columns, i // columns
        centre = (area.width * (column + 0.5) / columns, area.height * (row + 0.5) / rows)
        _star(surface, WHITE, centre, min(area.width / columns, area.height / rows) * 0.36)


def _emblem(surface: pygame.Surface, emblem: dict) -> None:
    width, height = surface.get_size()
    centre, color, kind = (width / 2, height / 2), tuple(emblem["color"]), emblem["kind"]
    if kind == "star":
        _star(surface, color, centre, height * 0.3)
    elif kind == "stars3":
        pygame.draw.circle(surface, (46, 110, 60), centre, height * 0.3, round(height * 0.04))
        for angle in (-90, 30, 150):
            radians = math.radians(angle)
            point = (
                centre[0] + math.cos(radians) * height * 0.13,
                centre[1] + math.sin(radians) * height * 0.13,
            )
            _star(surface, color, point, height * 0.09)
    elif kind == "sun":
        for ray in range(16):
            radians = math.radians(ray * 22.5)
            tip = (centre[0] + math.cos(radians) * height * 0.2, centre[1] + math.sin(radians) * height * 0.2)
            pygame.draw.line(surface, color, centre, tip, max(2, round(height * 0.025)))
        pygame.draw.circle(surface, color, centre, height * 0.1)
    elif kind == "eagle":
        # An eagle on a cactus, reduced to a wreathed brown badge.
        pygame.draw.circle(surface, (46, 110, 60), centre, height * 0.17, round(height * 0.03))
        pygame.draw.ellipse(
            surface,
            color,
            pygame.Rect(0, 0, height * 0.18, height * 0.22).move(
                centre[0] - height * 0.09, centre[1] - height * 0.12
            ),
        )


def _star(surface: pygame.Surface, color, centre: Point, radius: float) -> None:
    points = []
    for i in range(10):
        reach = radius if i % 2 == 0 else radius * 0.4
        radians = math.radians(-90 + i * 36)
        points.append((centre[0] + math.cos(radians) * reach, centre[1] + math.sin(radians) * reach))
    pygame.draw.polygon(surface, color, points)
