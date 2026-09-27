"""Georeferenced Natural Earth shaded relief, and the land and sea masks drawn from it.

Rendering only; nothing here affects topology or movement.
"""

from functools import lru_cache

import pygame

from cars.paths import content_path

# Raster bounds in degrees: west -180, east -30, north 80, south -60.
RASTER_WEST, RASTER_NORTH = -180, 80
RASTER_WIDTH_DEGREES, RASTER_HEIGHT_DEGREES = 150, 140
# The raster paints water in one pale blue; anything this close to it is sea.
RASTER_WATER = (118, 166, 202)
WATER_TOLERANCE = (34, 34, 34, 255)
# The masks are kept at a fraction of the raster's size: the land mask soft enough
# to anti-alias coasts, the shelf mask blurred into a glow that reaches offshore.
MASK_REDUCTION = 6
SHELF_REDUCTION = 60
# The blurred brightness that is taken out of the relief, leaving only its hill shading.
BRIGHTNESS_REDUCTION = 40
EDGE_FADE = 0.08  # Share of the raster, at each edge, over which land fades out.


@lru_cache(maxsize=1)
def relief_image() -> pygame.Surface:
    return pygame.image.load(str(content_path("map", "americas_relief.jpg"))).convert()


@lru_cache(maxsize=1)
def land_mask() -> pygame.Surface:
    """White where the raster shows land, black at sea, at a reduced size."""
    relief = relief_image()
    water = pygame.mask.from_threshold(relief, RASTER_WATER, WATER_TOLERANCE)
    water.invert()
    land = water.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0))
    width, height = relief.get_size()
    land = pygame.transform.smoothscale(land, (width // MASK_REDUCTION, height // MASK_REDUCTION))
    _fade_edges(land)
    return land


@lru_cache(maxsize=1)
def shelf_mask() -> pygame.Surface:
    """The land mask blurred outwards: bright near every coast, fading into the open sea."""
    mask = land_mask()
    size = mask.get_size()
    small = (size[0] * MASK_REDUCTION // SHELF_REDUCTION, size[1] * MASK_REDUCTION // SHELF_REDUCTION)
    blurred = pygame.transform.smoothscale(pygame.transform.smoothscale(mask, small), size)
    # Double it, so the fade reaches further offshore before it is gone.
    blurred.blit(blurred.copy(), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return blurred


@lru_cache(maxsize=1)
def relief_brightness() -> pygame.Surface:
    """The raster's overall brightness, blurred: its land cover and elevation tints."""
    relief = relief_image()
    width, height = relief.get_size()
    tiny = (width // (BRIGHTNESS_REDUCTION * 4), height // (BRIGHTNESS_REDUCTION * 4))
    small = (width // BRIGHTNESS_REDUCTION, height // BRIGHTNESS_REDUCTION)
    gray = pygame.transform.grayscale(pygame.transform.smoothscale(relief, small))
    return pygame.transform.smoothscale(pygame.transform.smoothscale(gray, tiny), small)


def _fade_edges(mask: pygame.Surface) -> None:
    """Darken a mask towards its edges, so land cut off by the raster fades away."""
    width, height = mask.get_size()
    margin_x, margin_y = round(width * EDGE_FADE), round(height * EDGE_FADE)
    for step in range(max(margin_x, margin_y)):
        keep = step / max(margin_x, margin_y)
        shade = (round(255 * keep),) * 3
        if step < margin_x:
            for x in (step, width - 1 - step):
                mask.fill(shade, pygame.Rect(x, 0, 1, height), special_flags=pygame.BLEND_RGB_MULT)
        if step < margin_y:
            for y in (step, height - 1 - step):
                mask.fill(shade, pygame.Rect(0, y, width, 1), special_flags=pygame.BLEND_RGB_MULT)
