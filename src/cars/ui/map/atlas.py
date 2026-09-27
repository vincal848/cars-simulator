"""The painted base map: relief, political colour, borders and coasts, in world pixels.

World pixel (0, 0) is the north-west corner of the relief raster, and one degree
is ``scale`` pixels. Each zoom level has its own Atlas, painted lazily in square
tiles that are kept once drawn, so panning only blits cached tiles. When a
province changes hands only the tiles it touches are repainted.

The look follows the modern grand-strategy map. Nations are clean colours over
the relief's hill shading, deepening towards their frontiers; the colour gives
way to the terrain as the camera comes in. The sea is a deep blue that lightens
towards every coast.
"""

import math
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

import pygame

from cars.ui.map.geometry import Border, Point, Rings
from cars.ui.map.nation_labels import NationNames, render
from cars.ui.map.relief import (
    RASTER_HEIGHT_DEGREES,
    RASTER_NORTH,
    RASTER_WEST,
    RASTER_WIDTH_DEGREES,
    land_mask,
    relief_brightness,
    relief_image,
    shelf_mask,
)

if TYPE_CHECKING:
    from cars.sim.state import GameState

TILE = 256
Color = tuple[int, int, int]
OPEN_SEA = (22, 50, 78)
SHELF = (58, 112, 140)  # The sea at the coast; it fades into OPEN_SEA offshore.
UNCLAIMED = (188, 188, 182)  # Land outside every province, such as Greenland.
# Hill shading: flat land sits at SHADE_MIDDLE, slopes are exaggerated SHADE_CONTRAST
# times, and no shadow is darker than SHADE_FLOOR (out of 255).
SHADE_MIDDLE = 222
SHADE_CONTRAST = 2
SHADE_FLOOR = 150
# How much of a nation's colour covers the terrain: most when zoomed out, least when in.
COLOUR_FAR, COLOUR_NEAR = 0.9, 0.55
FRONTIER_DEGREES = 1.3  # How far into a nation its colour deepens from the frontier.
FRONTIER_BANDS = 6
FRONTIER_ALPHA = 24  # Per band; the bands overlap into a gradient.
PROVINCE_LINE_ALPHA = 80
NATION_LINE = (24, 28, 34, 220)
TERRAIN_LINE = (120, 118, 110)
COAST_LINE = (16, 34, 50, 150)
FOG = (8, 14, 20, 105)


class Atlas:
    def __init__(
        self,
        state: "GameState",
        geometry: dict[str, list[Rings]],
        borders: list[Border],
        scale: float,
        names: NationNames | None = None,
        detail: bool = False,
        pixel: float = 1.0,
        fill: Callable[[str], Color | None] | None = None,
        zoom: float = 1.0,
    ) -> None:
        """``fill`` gives each province's colour for the map mode (None leaves bare relief;
        by default the controlling nation's colour). ``names`` letters nation names (zoomed
        out); ``detail`` draws heavier borders (zoomed in); ``pixel`` is the UI scale, for
        line widths and lettering; ``zoom`` sets how much of the terrain shows through."""
        self.state = state
        self.fill = fill or (
            lambda province: tuple(state.factions[state.provinces[province].controller].color)
        )
        self.scale = scale
        self.names = names
        self.detail = detail
        self.pixel = pixel
        closeness = min(1.0, max(0.0, (zoom - 1) / 3))
        self.colour_share = COLOUR_FAR + (COLOUR_NEAR - COLOUR_FAR) * closeness
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
        margin = self._frontier_width() + 2
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
                name = render(
                    self.state.factions[nation].name, curve, self.scale, self.names.font, self.pixel
                )
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
        """The raster at this zoom."""
        if self._relief is None:
            self._relief = pygame.transform.smoothscale(relief_image(), self.size)
        return self._relief

    def _paint(self, column: int, row: int) -> pygame.Surface:
        area = _tile_rect(column, row)
        terrain = pygame.Surface((TILE, TILE))
        terrain.blit(self.relief(), (0, 0), area)
        shade = _hill_shade(terrain, self._sample(relief_brightness(), area))
        tile = self._sea_and_bare_land(area, shade)

        provinces = [p for p, bounds in self.bounds.items() if bounds.colliderect(area)]
        borders = [
            i for i, bounds in enumerate(self.border_bounds) if bounds.colliderect(area.inflate(64, 64))
        ]
        by_fill: dict[Color | None, list[str]] = defaultdict(list)
        for province in provinces:
            by_fill[self.fill(province)].append(province)
        for color, members in sorted(by_fill.items(), key=lambda item: str(item[0])):
            tile.blit(self._land_layer(terrain, shade, area, color, members, borders), (0, 0))
        self._paint_borders(tile, area, borders)
        return tile

    def _sea_and_bare_land(self, area: pygame.Rect, shade: pygame.Surface) -> pygame.Surface:
        """Open sea lightening towards the coasts, with any land outside the provinces."""
        tile = pygame.Surface((TILE, TILE))
        tile.fill(OPEN_SEA)
        shelf = self._sample(shelf_mask(), area)
        shelf.fill([s - o for s, o in zip(SHELF, OPEN_SEA, strict=True)], special_flags=pygame.BLEND_RGB_MULT)
        tile.blit(shelf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        land = self._sample(land_mask(), area)
        sea = pygame.Surface((TILE, TILE))
        sea.fill((255, 255, 255))
        sea.blit(land, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
        tile.blit(sea, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        bare = shade.copy()
        bare.fill(UNCLAIMED, special_flags=pygame.BLEND_RGB_MULT)
        bare.blit(land, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        tile.blit(bare, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return tile

    def _sample(self, mask: pygame.Surface, area: pygame.Rect) -> pygame.Surface:
        """The part of a raster-wide ``mask`` under the world-pixel ``area``, at tile size."""
        kx, ky = mask.get_width() / self.size[0], mask.get_height() / self.size[1]
        tile = pygame.Surface((TILE, TILE))
        inside = area.clip(pygame.Rect(0, 0, *self.size))
        if inside.width < 1 or inside.height < 1:
            return tile
        source = pygame.Rect(
            math.floor(inside.x * kx),
            math.floor(inside.y * ky),
            max(1, math.ceil(inside.width * kx)),
            max(1, math.ceil(inside.height * ky)),
        ).clip(mask.get_rect())
        piece = pygame.transform.smoothscale(mask.subsurface(source), inside.size)
        tile.blit(piece, (inside.x - area.x, inside.y - area.y))
        return tile

    def _land_layer(self, terrain, shade, area, color: Color | None, members, borders) -> pygame.Surface:
        """The relief in ``color`` over its hill shading (bare relief for None), deepening
        towards its frontiers, cut to the land of ``members``."""
        layer = terrain.convert_alpha()
        if color is not None:
            coloured = shade.copy()
            coloured.fill(color, special_flags=pygame.BLEND_RGB_MULT)
            coloured.set_alpha(round(255 * self.colour_share))
            layer.blit(coloured, (0, 0))
            frontiers = [
                _shift(line, area)
                for border, line in (self.borders[index] for index in borders)
                if self._is_frontier(border) and any(self.fill(p) == color for p in border.provinces)
            ]
            deep = (*(round(c * 0.6) for c in color), FRONTIER_ALPHA)
            for band in range(FRONTIER_BANDS, 0, -1):
                stroke = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                width = max(2, round(self._frontier_width() * band / FRONTIER_BANDS))
                for points in frontiers:
                    _stroke(stroke, deep, points, width)
                layer.blit(stroke, (0, 0))
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
        nation_width = max(1, round((2 if self.detail else 1.5) * self.pixel))
        for index in borders:
            border, line = self.borders[index]
            points = _shift(line, area)
            if border.is_coast:
                pygame.draw.aalines(lines, COAST_LINE, False, points)
            elif self._is_frontier(border):
                _stroke(lines, NATION_LINE, points, nation_width)
            else:
                shade = tuple(int(c * 0.45) for c in self.fill(border.provinces[0]) or TERRAIN_LINE)
                pygame.draw.aalines(lines, (*shade, PROVINCE_LINE_ALPHA), False, points)
        tile.blit(lines, (0, 0))

    def _paint_fog(self, column: int, row: int) -> pygame.Surface:
        area = _tile_rect(column, row)
        fog = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        for province in self._hidden:
            if self.bounds[province].colliderect(area):
                for rings in self.polygons[province]:
                    pygame.draw.polygon(fog, FOG, _shift(rings[0], area))
        return fog

    def _is_frontier(self, border: Border) -> bool:
        return len({self.fill(p) for p in border.provinces}) > 1

    def _frontier_width(self) -> int:
        return max(4, round(FRONTIER_DEGREES * self.scale))


def _hill_shade(terrain: pygame.Surface, brightness: pygame.Surface) -> pygame.Surface:
    """The relief's hill shading as grey: its brightness less the blurred ``brightness``
    of the land around it, so only slopes show, not the raster's land cover. Sunlit
    slopes are near white, shadows down to SHADE_FLOOR."""
    gray = pygame.transform.grayscale(terrain)
    lighter = gray.copy()
    lighter.blit(brightness, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
    darker = brightness.copy()
    darker.blit(gray, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
    shade = pygame.Surface(terrain.get_size())
    shade.fill((SHADE_MIDDLE,) * 3)
    for _ in range(SHADE_CONTRAST):
        shade.blit(lighter, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        shade.blit(darker, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
    shade.fill((SHADE_FLOOR,) * 3, special_flags=pygame.BLEND_RGB_MAX)
    return shade


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


def _bounds(polygons: list[Rings]) -> pygame.Rect:
    xs = [x for rings in polygons for x, _ in rings[0]]
    ys = [y for rings in polygons for _, y in rings[0]]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 2, max(ys) - min(ys) + 2)


def _line_bounds(line: list[Point]) -> pygame.Rect:
    xs = [x for x, _ in line]
    ys = [y for _, y in line]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 2, max(ys) - min(ys) + 2)
