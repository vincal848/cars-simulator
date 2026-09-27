"""Georeferenced Natural Earth shaded relief, paper grain and engraved terrain symbols.

Rendering only; nothing here affects topology or movement.
"""

import random
from functools import lru_cache

import pygame

from cars.paths import content_path

# Raster bounds in degrees: west -180, east -30, north 80, south -60.
RASTER_WEST, RASTER_NORTH = -180, 80
RASTER_WIDTH_DEGREES, RASTER_HEIGHT_DEGREES = 150, 140
GRAIN_TILE = 256
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


def draw_trees(layer: pygame.Surface, x: float, y: float) -> None:
    for dx, dy in ((-5, 2), (0, -1), (5, 3)):
        crown = [(x + dx - 4, y + dy), (x + dx, y + dy - 8), (x + dx + 4, y + dy)]
        pygame.draw.line(layer, (65, 76, 45, 125), (x + dx, y + dy), (x + dx, y + dy + 4), 1)
        pygame.draw.polygon(layer, (91, 110, 67, 105), crown)
        pygame.draw.lines(layer, (49, 67, 46, 140), False, crown, 1)


def draw_peak(layer: pygame.Surface, x: float, y: float) -> None:
    pygame.draw.lines(layer, (92, 79, 58, 100), False, [(x - 9, y + 4), (x - 2, y - 7), (x + 7, y + 5)], 1)
    for i in range(4):
        pygame.draw.line(layer, (93, 77, 55, 90), (x - 2 + i, y - 6 + i * 2), (x - 1 + i, y + 2 + i), 1)
