"""Georeferenced Natural Earth shaded relief and the painted-atlas overlays drawn on it.

Rendering only; nothing here affects topology or movement.
"""

import random
from functools import lru_cache
from typing import TYPE_CHECKING

import pygame

from cars.paths import content_path
from cars.ui.art.lighting import light_field
from cars.ui.camera import Camera, point_in_polygon
from cars.ui.palette import CANVAS_SIZE, MAP_AREA

if TYPE_CHECKING:
    from cars.sim.state import GameState

# Raster bounds in degrees: west -180, east -30, north 80, south -60.
RASTER_WEST, RASTER_NORTH = -180, 80
RASTER_WIDTH_DEGREES, RASTER_HEIGHT_DEGREES = 150, 140
GRAIN_TILE = 256
GLAZE = (228, 204, 157, 22)
DETAIL_SCALE = 8  # Zoom level at which forest and mountain symbols appear.


@lru_cache(maxsize=1)
def relief_image() -> pygame.Surface:
    return pygame.image.load(str(content_path("map", "americas_relief.jpg"))).convert()


@lru_cache(maxsize=1)
def paper_grain() -> pygame.Surface:
    rng = random.Random(1840)
    tile = pygame.Surface((GRAIN_TILE, GRAIN_TILE), pygame.SRCALPHA)
    for _ in range(11000):
        x, y = rng.randrange(GRAIN_TILE), rng.randrange(GRAIN_TILE)
        tile.set_at((x, y), (79, 61, 36, rng.randrange(3, 17)))
    return tile


def project_relief(camera: Camera) -> pygame.Surface:
    """The relief raster, lit and glazed, scaled and positioned for ``camera``."""
    result = pygame.Surface(MAP_AREA.size, pygame.SRCALPHA)
    top_left = camera.project((RASTER_WEST, RASTER_NORTH))
    size = (round(RASTER_WIDTH_DEGREES * camera.scale), round(RASTER_HEIGHT_DEGREES * camera.scale))
    scaled = pygame.transform.smoothscale(relief_image(), size)
    scaled.blit(
        pygame.transform.smoothscale(light_field(), size), (0, 0), special_flags=pygame.BLEND_RGB_MULT
    )
    glaze = pygame.Surface(size, pygame.SRCALPHA)
    glaze.fill(GLAZE)
    scaled.blit(glaze, (0, 0))
    grain = paper_grain()
    for x in range(0, size[0], GRAIN_TILE):
        for y in range(0, size[1], GRAIN_TILE):
            scaled.blit(grain, (x, y))
    for shift in (-2, -1, 0, 1, 2):
        result.blit(scaled, (top_left[0] + shift * camera.period, top_left[1]))
    return result


def illustration_layer(state: "GameState", parts: dict, scale: float) -> pygame.Surface:
    """Sparse engraved forest and mountain symbols, clipped to each province's land."""
    layer = pygame.Surface(MAP_AREA.size, pygame.SRCALPHA)
    if scale < DETAIL_SCALE:
        return layer
    for province_id, polygons in parts.items():
        terrain = state.provinces[province_id].terrain
        if terrain not in ("forest", "mountains"):
            continue
        rng = random.Random(province_id)
        for rings in polygons:
            outer, holes = rings[0], rings[1:]
            low = (min(x for x, y in outer), min(y for x, y in outer))
            high = (max(x for x, y in outer), max(y for x, y in outer))
            for _ in range(3):
                x, y = rng.uniform(low[0], high[0]), rng.uniform(low[1], high[1])
                if not (15 < x < CANVAS_SIZE[0] - 20 and 15 < y < MAP_AREA.height - 17):
                    continue
                corners = [(x - 10, y - 10), (x + 10, y - 10), (x - 10, y + 8), (x + 10, y + 8)]
                on_land = all(
                    point_in_polygon(p, outer) and not any(point_in_polygon(p, h) for h in holes)
                    for p in corners
                )
                if not on_land:
                    continue
                if terrain == "forest":
                    _draw_trees(layer, x, y)
                else:
                    _draw_peak(layer, x, y)
    return layer


def _draw_trees(layer: pygame.Surface, x: float, y: float) -> None:
    for dx, dy in ((-5, 2), (0, -1), (5, 3)):
        crown = [(x + dx - 4, y + dy), (x + dx, y + dy - 8), (x + dx + 4, y + dy)]
        pygame.draw.line(layer, (65, 76, 45, 125), (x + dx, y + dy), (x + dx, y + dy + 4), 1)
        pygame.draw.polygon(layer, (91, 110, 67, 105), crown)
        pygame.draw.lines(layer, (49, 67, 46, 140), False, crown, 1)


def _draw_peak(layer: pygame.Surface, x: float, y: float) -> None:
    pygame.draw.lines(layer, (92, 79, 58, 100), False, [(x - 9, y + 4), (x - 2, y - 7), (x + 7, y + 5)], 1)
    for i in range(4):
        pygame.draw.line(layer, (93, 77, 55, 90), (x - 2 + i, y - 6 + i * 2), (x - 1 + i, y + 2 + i), 1)
