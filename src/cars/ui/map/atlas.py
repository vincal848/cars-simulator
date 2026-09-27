"""The painted base map: relief, political colour, borders and coasts, in world pixels.

World pixel (0, 0) is the north-west corner of the relief raster, and one degree
is ``scale`` pixels. Each zoom level has its own Atlas, painted lazily in square
tiles that are kept once drawn, so panning only blits cached tiles. When a
province changes hands only the tiles it touches are repainted.

The look follows the grand-strategy atlas convention: the relief shows through
translucent nation colours, provinces are separated by faint lines and nations
by strong dark ones with a glow of their colour inside, and the sea is a dark
wash with lighter shallows along the coast.
"""

import math
import random
from collections import defaultdict
from typing import TYPE_CHECKING

import pygame

from cars.ui.art.lighting import light_field
from cars.ui.camera import point_in_polygon
from cars.ui.map.geometry import Border, Point, Rings
from cars.ui.map.nation_labels import NationNames, render
from cars.ui.map.relief import (
    DETAIL_SCALE,
    RASTER_HEIGHT_DEGREES,
    RASTER_NORTH,
    RASTER_WEST,
    RASTER_WIDTH_DEGREES,
    draw_peak,
    draw_trees,
    paper_grain,
    relief_image,
)

if TYPE_CHECKING:
    from cars.sim.state import GameState

TILE = 256
OPEN_SEA = (35, 62, 83)  # The graded raster sea at its edges, so the two meet unseen.
SEA_GRADE = (80, 102, 112)  # Multiplies the raster's sea (and unclaimed land) into a dark wash.
# The colour that SEA_GRADE turns into OPEN_SEA, used to fade out the raster's edges.
RAW_SEA = tuple(min(255, round(sea * 255 / grade)) for sea, grade in zip(OPEN_SEA, SEA_GRADE, strict=True))
SEA_EDGE_DEGREES = 12  # The raster fades into the open sea over this margin.
SHALLOWS = [(1.4, (104, 150, 150, 26)), (0.6, (132, 170, 160, 38))]  # (width in degrees, colour)
LAND_TINT = 92  # Opacity of the flat nation colour laid over the dyed relief.
EDGE_GLOW_DEGREES = 1.1
EDGE_GLOW_ALPHA = 70  # Per band; three bands overlap into a gradient at the frontier.
PROVINCE_LINE_ALPHA = 120
NATION_LINE = (34, 27, 23)
COAST_LINE = (26, 38, 40, 210)
FOG = (8, 14, 20, 105)
SYMBOLS_PER_PROVINCE = 3
NAMES_BELOW_SCALE = 8  # Zoomed in further, province names take over from nation names.


class Atlas:
    def __init__(
        self,
        state: "GameState",
        geometry: dict[str, list[Rings]],
        borders: list[Border],
        scale: float,
        names: NationNames | None = None,
    ) -> None:
        self.state = state
        self.scale = scale
        self.names = names if scale < NAMES_BELOW_SCALE else None
        self._lettering: list[tuple[pygame.Surface, pygame.Rect]] | None = None
        self.size = (math.ceil(RASTER_WIDTH_DEGREES * scale), math.ceil(RASTER_HEIGHT_DEGREES * scale))
        self.columns = math.ceil(self.size[0] / TILE)
        self.rows = math.ceil(self.size[1] / TILE)
        self.polygons = {
            province: [[[self.world(point) for point in ring] for ring in rings] for rings in polygons]
            for province, polygons in geometry.items()
        }
        self.bounds = {province: _bounds(polygons) for province, polygons in self.polygons.items()}
        self.borders = [(border, [self.world(point) for point in border.line]) for border in borders]
        self.border_bounds = [_line_bounds(line) for _, line in self.borders]
        self.symbols = _symbols(state, self.polygons) if scale >= DETAIL_SCALE else {}
        self._relief: pygame.Surface | None = None
        self._tiles: dict[tuple[int, int], pygame.Surface] = {}
        self._fog_tiles: dict[tuple[int, int], pygame.Surface] = {}
        self._hidden: frozenset[str] = frozenset()

    def world(self, point: Point) -> Point:
        longitude, latitude = point
        return (longitude - RASTER_WEST) * self.scale, (RASTER_NORTH - latitude) * self.scale

    # Drawing --------------------------------------------------------------------------

    def draw(self, screen: pygame.Surface, origin: tuple[int, int], period: float, area: pygame.Rect) -> None:
        """Blit every tile inside ``area``; ``origin`` is where world (0, 0) falls on screen."""
        screen.fill(OPEN_SEA, area)
        for x, y, key in self._visible_tiles(origin, period, area):
            screen.blit(self.tile(*key), (x, y))

    def draw_fog(
        self,
        screen: pygame.Surface,
        origin: tuple[int, int],
        period: float,
        area: pygame.Rect,
        hidden: set[str],
    ) -> None:
        """Shade the ``hidden`` provinces."""
        hidden = frozenset(hidden)
        if hidden != self._hidden:
            self._hidden = hidden
            self._fog_tiles.clear()
        for x, y, key in self._visible_tiles(origin, period, area):
            if key not in self._fog_tiles:
                self._fog_tiles[key] = self._paint_fog(*key)
            screen.blit(self._fog_tiles[key], (x, y))

    def _visible_tiles(self, origin, period, area):
        for shift in range(-2, 3):
            left = origin[0] + round(shift * period)
            if left + self.size[0] <= area.left or left >= area.right:
                continue
            first_column = max(0, (area.left - left) // TILE)
            last_column = min(self.columns - 1, (area.right - 1 - left) // TILE)
            first_row = max(0, (area.top - origin[1]) // TILE)
            last_row = min(self.rows - 1, (area.bottom - 1 - origin[1]) // TILE)
            for column in range(first_column, last_column + 1):
                for row in range(first_row, last_row + 1):
                    yield left + column * TILE, origin[1] + row * TILE, (column, row)

    def invalidate(self, provinces: set[str]) -> None:
        """Forget the tiles ``provinces`` touch, so they are repainted in new colours, and
        letter the nations' names afresh."""
        margin = self._glow_width() + 2
        for province in provinces:
            area = self.bounds[province].inflate(margin * 2, margin * 2)
            for key in [key for key in self._tiles if _tile_rect(*key).colliderect(area)]:
                del self._tiles[key]
        self._lettering = None

    def draw_names(
        self, screen: pygame.Surface, origin: tuple[int, int], period: float, area: pygame.Rect
    ) -> None:
        """Nation names, drawn over the tiles and the fog so they stay legible."""
        for shift in range(-2, 3):
            left = origin[0] + round(shift * period)
            for lettering, rect in self.lettering():
                placed = rect.move(left, origin[1])
                if placed.colliderect(area):
                    screen.blit(lettering, placed)

    def lettering(self) -> list[tuple[pygame.Surface, pygame.Rect]]:
        """Each nation's name, rendered for this zoom, with its world-pixel rectangle."""
        if self._lettering is None:
            self._lettering = []
            for nation, curve in self.names.curves() if self.names else []:
                name = render(self.state.factions[nation].name, curve, self.scale, self.names.font)
                if name:
                    self._lettering.append(name)
        return self._lettering

    # Painting -------------------------------------------------------------------------

    def tile(self, column: int, row: int) -> pygame.Surface:
        key = (column, row)
        if key not in self._tiles:
            self._tiles[key] = self._paint(column, row)
        return self._tiles[key]

    def relief(self) -> pygame.Surface:
        """The raster at this zoom, lit, with its edges faded into the open sea."""
        if self._relief is None:
            relief = pygame.transform.smoothscale(relief_image(), self.size)
            light = pygame.transform.smoothscale(light_field(), self.size)
            relief.blit(light, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            _fade_edges(relief, round(SEA_EDGE_DEGREES * self.scale))
            self._relief = relief
        return self._relief

    def _paint(self, column: int, row: int) -> pygame.Surface:
        area = _tile_rect(column, row)
        land = pygame.Surface((TILE, TILE))
        land.fill(RAW_SEA)
        land.blit(self.relief(), (0, 0), area)
        tile = land.copy()
        tile.fill(SEA_GRADE, special_flags=pygame.BLEND_RGB_MULT)

        provinces = [p for p, bounds in self.bounds.items() if bounds.colliderect(area)]
        borders = [
            i for i, bounds in enumerate(self.border_bounds) if bounds.colliderect(area.inflate(64, 64))
        ]
        self._paint_shallows(tile, area, borders)
        by_nation: dict[str, list[str]] = defaultdict(list)
        for province in provinces:
            by_nation[self.state.provinces[province].controller].append(province)
        for nation, members in sorted(by_nation.items()):
            tile.blit(self._nation_layer(land, area, nation, members, borders), (0, 0))
        self._paint_symbols(tile, area, provinces)
        self._paint_borders(tile, area, borders)
        grain = paper_grain()
        tile.blit(grain, (0, 0))
        return tile

    def _paint_shallows(self, tile: pygame.Surface, area: pygame.Rect, borders: list[int]) -> None:
        layer = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        for width, color in SHALLOWS:
            stroke = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pixels = max(2, round(width * self.scale))
            for index in borders:
                border, line = self.borders[index]
                if border.is_coast:
                    _stroke(stroke, color, _shift(line, area), pixels)
            layer.blit(stroke, (0, 0))
        tile.blit(layer, (0, 0))

    def _nation_layer(self, land, area, nation, members, borders) -> pygame.Surface:
        """Relief tinted in ``nation``'s colour, with a glow along its frontiers, cut to its land."""
        color = self.state.factions[nation].color
        layer = land.convert_alpha()
        # Dye the relief so its shading survives, then lay the flat colour over it.
        layer.fill([int(c * 0.6 + 102) for c in color], special_flags=pygame.BLEND_RGB_MULT)
        tint = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        tint.fill((*color, LAND_TINT))
        layer.blit(tint, (0, 0))
        frontiers = [
            _shift(line, area)
            for border, line in (self.borders[index] for index in borders)
            if self._is_frontier(border) and any(self._controller(p) == nation for p in border.provinces)
        ]
        glow_color = (*_brighten(color), EDGE_GLOW_ALPHA)
        for fraction in (1, 0.66, 0.33):
            band = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            for points in frontiers:
                _stroke(band, glow_color, points, max(2, round(self._glow_width() * fraction)))
            layer.blit(band, (0, 0))
        mask = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        for province in members:
            for rings in self.polygons[province]:
                pygame.draw.polygon(mask, (255, 255, 255, 255), _shift(rings[0], area))
                for hole in rings[1:]:
                    pygame.draw.polygon(mask, (0, 0, 0, 0), _shift(hole, area))
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return layer

    def _paint_borders(self, tile: pygame.Surface, area: pygame.Rect, borders: list[int]) -> None:
        lines = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        nation_width = 2 if self.scale < 10 else 3
        for index in borders:
            border, line = self.borders[index]
            points = _shift(line, area)
            if border.is_coast:
                pygame.draw.aalines(lines, COAST_LINE, False, points)
            elif self._is_frontier(border):
                _stroke(lines, NATION_LINE, points, nation_width)
            else:
                shade = tuple(
                    int(c * 0.5) for c in self.state.factions[self._controller(border.provinces[0])].color
                )
                pygame.draw.aalines(lines, (*shade, PROVINCE_LINE_ALPHA), False, points)
        tile.blit(lines, (0, 0))

    def _paint_symbols(self, tile: pygame.Surface, area: pygame.Rect, provinces: list[str]) -> None:
        for province in provinces:
            terrain = self.state.provinces[province].terrain
            for x, y in self.symbols.get(province, ()):
                if area.inflate(24, 24).collidepoint(x, y):
                    draw = draw_trees if terrain == "forest" else draw_peak
                    draw(tile, x - area.x, y - area.y)

    def _paint_fog(self, column: int, row: int) -> pygame.Surface:
        area = _tile_rect(column, row)
        fog = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        for province in self._hidden:
            if self.bounds[province].colliderect(area):
                for rings in self.polygons[province]:
                    pygame.draw.polygon(fog, FOG, _shift(rings[0], area))
        return fog

    def _controller(self, province: str) -> str:
        return self.state.provinces[province].controller

    def _is_frontier(self, border: Border) -> bool:
        return len({self._controller(p) for p in border.provinces}) > 1

    def _glow_width(self) -> int:
        return max(3, round(EDGE_GLOW_DEGREES * self.scale))


def _fade_edges(surface: pygame.Surface, margin: int) -> None:
    """Blend a surface's rectangular edges into the open sea over ``margin`` pixels."""
    width, height = surface.get_size()
    across = pygame.Surface((width, 1), pygame.SRCALPHA)
    down = pygame.Surface((1, height), pygame.SRCALPHA)
    for step in range(margin):
        alpha = round(255 * (1 - step / margin) ** 2)
        across.fill((*RAW_SEA, alpha))
        down.fill((*RAW_SEA, alpha))
        surface.blit(across, (0, step))
        surface.blit(across, (0, height - 1 - step))
        surface.blit(down, (step, 0))
        surface.blit(down, (width - 1 - step, 0))


def _tile_rect(column: int, row: int) -> pygame.Rect:
    return pygame.Rect(column * TILE, row * TILE, TILE, TILE)


def _shift(points, area: pygame.Rect) -> list[Point]:
    return [(x - area.x, y - area.y) for x, y in points]


def _stroke(surface: pygame.Surface, color, points: list[Point], width: int) -> None:
    """A thick polyline with rounded joints, so wide strokes have no notches."""
    if len(points) < 2:
        return
    pygame.draw.lines(surface, color, False, points, width)
    if width > 2:
        for point in points:
            pygame.draw.circle(surface, color, point, width / 2 - 0.5)


def _brighten(color) -> tuple[int, int, int]:
    return tuple(min(255, int(c * 1.15 + 20)) for c in color)


def _bounds(polygons: list[Rings]) -> pygame.Rect:
    xs = [x for rings in polygons for x, _ in rings[0]]
    ys = [y for rings in polygons for _, y in rings[0]]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 2, max(ys) - min(ys) + 2)


def _line_bounds(line: list[Point]) -> pygame.Rect:
    xs = [x for x, _ in line]
    ys = [y for _, y in line]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 2, max(ys) - min(ys) + 2)


def _symbols(state: "GameState", polygons: dict[str, list[Rings]]) -> dict[str, list[Point]]:
    """A few engraved forest or mountain symbols per province, placed wholly on its land."""
    symbols: dict[str, list[Point]] = {}
    for province, parts in polygons.items():
        if state.provinces[province].terrain not in ("forest", "mountains"):
            continue
        rng = random.Random(province)
        placed = []
        for rings in parts:
            outer, holes = rings[0], rings[1:]
            low = (min(x for x, _ in outer), min(y for _, y in outer))
            high = (max(x for x, _ in outer), max(y for _, y in outer))
            for _ in range(SYMBOLS_PER_PROVINCE):
                x, y = rng.uniform(low[0], high[0]), rng.uniform(low[1], high[1])
                corners = [(x - 10, y - 10), (x + 10, y - 10), (x - 10, y + 8), (x + 10, y + 8)]
                if all(
                    point_in_polygon(p, outer) and not any(point_in_polygon(p, h) for h in holes)
                    for p in corners
                ):
                    placed.append((x, y))
        symbols[province] = placed
    return symbols
