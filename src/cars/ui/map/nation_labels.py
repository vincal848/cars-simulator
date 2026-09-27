"""Nation names lettered across their territory, as on a political atlas.

Each nation's land is rasterised coarsely and split into connected territories.
A territory's principal axis and the midline of its land along that axis give
a gentle curve, and the name is set along the curve at the largest size that
fits. Layouts are in degrees, so every zoom level shares them; only the lettering
is rendered per zoom.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING

import pygame

from cars.ui.map.geometry import Rings
from cars.ui.map.relief import RASTER_NORTH, RASTER_WEST
from cars.ui.typography import DEFAULT_FONT, TITLE, load_font

if TYPE_CHECKING:
    from cars.sim.state import GameState

RESOLUTION = 2  # Raster pixels per degree.
MIN_AREA = 12  # Territories smaller than this many raster pixels go unnamed.
MAX_TILT = 50  # Degrees; steeper territories are lettered at this angle.
MIN_SIZE, MAX_SIZE = 10, 54  # Letter height in screen pixels.
SPACING = 0.16  # Extra space between letters, as a fraction of the letter height.
INK = (24, 18, 14, 225)
# Where to try a name that does not fit in the middle: fractions of the spare length
# along the curve, and of the territory's width across it.
ALONG = (0, -0.2, 0.2, -0.4, 0.4)
ACROSS = (0, -0.25, 0.25)


class NationNames:
    """Name curves for every nation's territory, recomputed only for nations whose land changed."""

    def __init__(self, state: "GameState", geometry: dict[str, list[Rings]]) -> None:
        self.state = state
        self.geometry = geometry
        self._curves: dict[tuple[str, frozenset[str]], list[NameCurve]] = {}
        self._fonts: dict[int, pygame.font.Font] = {}

    def font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            self._fonts[size] = load_font(DEFAULT_FONT, size, TITLE)
        return self._fonts[size]

    def curves(self) -> list[tuple[str, "NameCurve"]]:
        held: dict[str, set[str]] = {}
        for province in self.state.provinces.values():
            held.setdefault(province.controller, set()).add(province.id)
        current = {(nation, frozenset(provinces)) for nation, provinces in held.items()}
        for key in list(self._curves):
            if key not in current:
                del self._curves[key]
        result = []
        for key in sorted(current, key=lambda key: key[0]):
            if key not in self._curves:
                self._curves[key] = territories([self.geometry[p] for p in sorted(key[1])])
            result += [(key[0], curve) for curve in self._curves[key]]
        return result


@dataclass(frozen=True)
class NameCurve:
    """Where a territory's name runs: a quadratic bend around a straight axis, in raster pixels."""

    center: tuple[float, float]
    axis: tuple[float, float]  # unit vector along the name, pointing right
    bend: tuple[float, float, float]  # offset across the axis = a·t² + b·t + c
    start: float  # usable stretch along the axis
    end: float
    thickness: float  # typical width of land across the usable stretch
    land: pygame.mask.Mask = field(compare=False, repr=False)
    origin: tuple[float, float] = field(compare=False, repr=False)  # raster position of land's (0, 0)

    def point(self, t: float, shift: float = 0) -> tuple[float, float]:
        """The point ``t`` along the curve, moved ``shift`` across it (for a second line)."""
        a, b, c = self.bend
        offset = a * t * t + b * t + c + shift
        ux, uy = self.axis
        return self.center[0] + ux * t - uy * offset, self.center[1] + uy * t + ux * offset

    def on_land(self, x: float, y: float) -> bool:
        column, row = round(x - self.origin[0]), round(y - self.origin[1])
        width, height = self.land.get_size()
        return 0 <= column < width and 0 <= row < height and bool(self.land.get_at((column, row)))


def territories(polygons: list[list[Rings]]) -> list[NameCurve]:
    """Name curves for each sizeable connected territory of one nation."""
    points = [p for rings in (r for group in polygons for r in group) for p in rings[0]]
    west = min(x for x, _ in points)
    north = max(y for _, y in points)
    east = max(x for x, _ in points)
    south = min(y for _, y in points)
    origin = ((west - RASTER_WEST) * RESOLUTION - 2, (RASTER_NORTH - north) * RESOLUTION - 2)
    size = (math.ceil((east - west) * RESOLUTION) + 5, math.ceil((north - south) * RESOLUTION) + 5)
    surface = pygame.Surface(size, pygame.SRCALPHA)
    for group in polygons:
        for rings in group:
            outline = [_raster(p, origin) for p in rings[0]]
            if len(outline) > 2:
                pygame.draw.polygon(surface, (255, 255, 255, 255), outline)
    land = pygame.mask.from_surface(surface)
    curves = []
    for part in land.connected_components(MIN_AREA):
        fit = _fit(part)
        if fit:
            (cx, cy), axis, bend, start, end, thickness = fit
            curves.append(
                NameCurve((cx + origin[0], cy + origin[1]), axis, bend, start, end, thickness, part, origin)
            )
    return curves


def render(
    name: str,
    curve: NameCurve,
    scale: float,
    font: Callable[[int], pygame.font.Font],
    pixel: float = 1.0,
) -> tuple[pygame.Surface, pygame.Rect] | None:
    """The name lettered along ``curve`` for a map at ``scale`` pixels per degree, with its
    world-pixel rectangle; None when it cannot be set legibly inside the territory.
    ``pixel`` is the UI scale, which scales the smallest and largest letter sizes.

    Tries one line, then two, from the largest size down, sliding the name along
    and across the curve, and accepts the first setting whose every letter stands
    on the territory's land.
    """
    zoom = scale / RESOLUTION
    words = name.upper().split()
    settings = [[" ".join(words)]]
    if len(words) > 1:
        split = min(
            range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:])))
        )
        settings.append([" ".join(words[:split]), " ".join(words[split:])])
    for lines in settings:
        largest = min(round(MAX_SIZE * pixel), int(curve.thickness * zoom * 0.62 / len(lines)))
        for size in range(largest, round(MIN_SIZE * pixel) - 1, -1):
            for across in ACROSS:
                for along in ALONG:
                    glyphs = _set(lines, font(size), curve, zoom, along, across * curve.thickness)
                    if glyphs is None:
                        break
                    if all(_stands_on_land(curve, glyph, size, zoom) for glyph in glyphs):
                        return _draw(glyphs, font(size))
    return None


def _set(
    lines: list[str], font: pygame.font.Font, curve: NameCurve, zoom: float, along: float, across: float
):
    """Letter positions and angles for ``lines`` along the curve, or None if a line is too long.

    ``along`` slides the name from the middle by that fraction of the spare length;
    ``across`` moves it off the curve by that many raster pixels.
    """
    size = font.get_height()
    length = (curve.end - curve.start) * zoom * 0.94
    placed = []
    for index, line in enumerate(lines):
        width = _text_width(line, font)
        if width > length:
            return None
        shift = (index - (len(lines) - 1) / 2) * size * 1.02 / zoom + across
        samples = [curve.point(curve.start + (curve.end - curve.start) * i / 64, shift) for i in range(65)]
        path = [(x * zoom, y * zoom) for x, y in samples]
        distances = [0.0]
        for a, b in pairwise(path):
            distances.append(distances[-1] + math.dist(a, b))
        cursor = (distances[-1] - width) * (0.5 + along)
        for letter in line:
            advance = font.size(letter)[0] + size * SPACING
            position, angle = _along(path, distances, cursor + advance / 2)
            cursor += advance
            if letter != " ":
                placed.append((letter, position, angle))
    return placed


def _stands_on_land(curve: NameCurve, glyph, size: int, zoom: float) -> bool:
    """Whether a letter's middle, top and bottom all fall on the territory's land."""
    _, (x, y), angle = glyph
    nx, ny = -math.sin(angle), math.cos(angle)
    reach = size * 0.38
    return all(curve.on_land((x + nx * d) / zoom, (y + ny * d) / zoom) for d in (-reach, 0, reach))


def _draw(glyphs, font: pygame.font.Font) -> tuple[pygame.Surface, pygame.Rect]:
    stamps = []
    for letter, (x, y), angle in glyphs:
        glyph = pygame.transform.rotozoom(font.render(letter, True, INK[:3]), -math.degrees(angle), 1)
        stamps.append((glyph, glyph.get_rect(center=(round(x), round(y)))))
    bounds = stamps[0][1].unionall([rect for _, rect in stamps])
    surface = pygame.Surface(bounds.size, pygame.SRCALPHA)
    for glyph, rect in stamps:
        surface.blit(glyph, rect.move(-bounds.x, -bounds.y))
    surface.fill((255, 255, 255, INK[3]), special_flags=pygame.BLEND_RGBA_MULT)
    return surface, bounds


def _raster(point, origin) -> tuple[float, float]:
    longitude, latitude = point
    return (longitude - RASTER_WEST) * RESOLUTION - origin[0], (
        RASTER_NORTH - latitude
    ) * RESOLUTION - origin[1]


def _fit(mask: pygame.mask.Mask) -> tuple | None:
    """(centre, axis, bend, start, end, thickness) of a territory, in the mask's pixels."""
    width, height = mask.get_size()
    pixels = [(x, y) for y in range(0, height) for x in range(0, width) if mask.get_at((x, y))]
    count = len(pixels)
    cx = sum(x for x, _ in pixels) / count
    cy = sum(y for _, y in pixels) / count
    sxx = sum((x - cx) ** 2 for x, _ in pixels) / count
    syy = sum((y - cy) ** 2 for _, y in pixels) / count
    sxy = sum((x - cx) * (y - cy) for x, y in pixels) / count
    angle = 0.5 * math.atan2(2 * sxy, sxx - syy)
    angle = max(-math.radians(MAX_TILT), min(math.radians(MAX_TILT), angle))
    axis = (math.cos(angle), math.sin(angle))
    along = [(x - cx) * axis[0] + (y - cy) * axis[1] for x, y in pixels]
    runs = []
    for t in range(math.floor(min(along)), math.ceil(max(along)) + 1):
        run = _run_across(mask, cx, cy, axis, t)
        if run:
            runs.append((t, *run))
    if len(runs) < 3:
        return None
    widest = max(length for _, _, length in runs)
    usable = [(t, middle, length) for t, middle, length in runs if length >= widest * 0.3]
    start, end = usable[0][0], usable[-1][0]
    bend = _quadratic([(t, middle) for t, middle, _ in usable])
    thickness = sorted(length for _, _, length in usable)[len(usable) // 4]
    return (cx, cy), axis, bend, start, end, thickness


def _run_across(mask, cx, cy, axis, t) -> tuple[float, float] | None:
    """The longest stretch of land crossing the axis at ``t``: (its middle, its length)."""
    ux, uy = axis
    width, height = mask.get_size()
    best, current = None, None
    reach = int(math.hypot(width, height))
    for s in range(-reach, reach + 1):
        x, y = round(cx + ux * t - uy * s), round(cy + uy * t + ux * s)
        inside = 0 <= x < width and 0 <= y < height and mask.get_at((x, y))
        if inside:
            current = (current[0], s) if current else (s, s)
        elif current:
            if best is None or current[1] - current[0] > best[1] - best[0]:
                best = current
            current = None
    if best is None:
        return None
    return (best[0] + best[1]) / 2, best[1] - best[0] + 1


def _quadratic(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Least-squares a·t² + b·t + c through ``points``, with the bend kept gentle."""
    n = len(points)
    sums = [sum(t**k for t, _ in points) for k in range(5)]
    rhs = [sum(v * t**k for t, v in points) for k in range(3)]
    matrix = [[sums[4], sums[3], sums[2]], [sums[3], sums[2], sums[1]], [sums[2], sums[1], n]]
    try:
        a, b, c = _solve(matrix, [rhs[2], rhs[1], rhs[0]])
    except ZeroDivisionError:
        return 0.0, 0.0, sum(v for _, v in points) / n
    half = max(abs(points[0][0]), abs(points[-1][0]), 1)
    limit = 0.12 / half  # At most about an eighth of the half-length of sag.
    return max(-limit, min(limit, a)), b, c


def _solve(matrix, vector) -> list[float]:
    """Gaussian elimination for a system of three equations."""
    rows = [[*row, value] for row, value in zip(matrix, vector, strict=True)]
    for i in range(3):
        pivot = max(range(i, 3), key=lambda r: abs(rows[r][i]))
        rows[i], rows[pivot] = rows[pivot], rows[i]
        if abs(rows[i][i]) < 1e-12:
            raise ZeroDivisionError
        for r in range(3):
            if r != i:
                factor = rows[r][i] / rows[i][i]
                rows[r] = [a - factor * b for a, b in zip(rows[r], rows[i], strict=True)]
    return [rows[i][3] / rows[i][i] for i in range(3)]


def _along(path, distances, distance) -> tuple[tuple[float, float], float]:
    """The point ``distance`` along a polyline and the direction of travel there."""
    distance = max(0.0, min(distances[-1], distance))
    for i in range(1, len(path)):
        if distances[i] >= distance or i == len(path) - 1:
            (ax, ay), (bx, by) = path[i - 1], path[i]
            span = distances[i] - distances[i - 1] or 1
            f = (distance - distances[i - 1]) / span
            return (ax + (bx - ax) * f, ay + (by - ay) * f), math.atan2(by - ay, bx - ax)
    return path[-1], 0.0


def _text_width(letters: str, font: pygame.font.Font) -> float:
    spacing = font.get_height() * SPACING
    return sum(font.size(letter)[0] + spacing for letter in letters) - spacing
