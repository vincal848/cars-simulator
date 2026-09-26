"""A single north-west key light with soft ambient variation, and ground shadows.

The terrain raster already contains Natural Earth hillshade. This adds a restrained
warm/cool light field; it is not an elevation model or a day/night cycle.
"""

import math
from functools import lru_cache

import pygame

LIGHT_FIELD_SIZE = (120, 112)
SHADOW = (13, 19, 26)

_shadows: dict[tuple[int, int], pygame.Surface] = {}


@lru_cache(maxsize=1)
def light_field(size: tuple[int, int] = LIGHT_FIELD_SIZE) -> pygame.Surface:
    surface = pygame.Surface(size)
    for y in range(size[1]):
        for x in range(size[0]):
            u = x / (size[0] - 1)
            v = y / (size[1] - 1)
            cloud = (math.sin(u * 17 + v * 7) + math.cos(v * 19 - u * 5)) * 0.5
            exposure = 245 - 12 * (u + v) / 2 + 5 * cloud
            color = (min(255, int(exposure + 5)), int(exposure), min(255, int(exposure + 2 * v - 5)))
            surface.set_at((x, y), color)
    return surface


def contact_shadow(screen: pygame.Surface, center, size: tuple[int, int] = (38, 17)) -> None:
    """Soft ground shadow cast south-east from an object's base."""
    if size not in _shadows:
        small = pygame.Surface((size[0] // 2 + 6, size[1] // 2 + 6), pygame.SRCALPHA)
        for inset, alpha in [(0, 10), (2, 20), (4, 35)]:
            pygame.draw.ellipse(small, (*SHADOW, alpha), small.get_rect().inflate(-inset, -inset))
        _shadows[size] = pygame.transform.smoothscale(small, size)
    screen.blit(_shadows[size], (center[0] - size[0] * 0.28, center[1] - size[1] * 0.35))
