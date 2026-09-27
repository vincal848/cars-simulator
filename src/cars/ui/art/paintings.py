"""Optional painted artwork: event illustrations, leader portraits and the title backdrop.

A painting is a PNG or JPEG at ``gfx/paintings/<kind>/<key>`` in the content folder
or in a mod. The game ships without them; wherever one is missing, the caller
draws its procedural art instead. docs/ART.md specifies every painting.
"""

import pygame

from cars.paths import find_asset

EVENTS, LEADERS, TITLE = "events", "leaders", "title"
EXTENSIONS = (".png", ".jpg")

_cache: dict[tuple[str, str, tuple[int, int]], pygame.Surface | None] = {}


def painting(kind: str, key: str, size: tuple[int, int]) -> pygame.Surface | None:
    """The painting scaled and cropped to fill ``size``, or None if there is none."""
    cache_key = (kind, key, size)
    if cache_key not in _cache:
        _cache[cache_key] = _load(kind, key, size)
    return _cache[cache_key]


def _load(kind: str, key: str, size: tuple[int, int]) -> pygame.Surface | None:
    path = next(
        (found for found in (find_asset("gfx", "paintings", kind, key + ext) for ext in EXTENSIONS) if found),
        None,
    )
    if path is None:
        return None
    try:
        image = pygame.image.load(str(path)).convert()
    except (pygame.error, OSError):
        return None
    # Cover the target: scale until both sides fit, then crop the overflow evenly.
    width, height = image.get_size()
    factor = max(size[0] / width, size[1] / height)
    scaled = pygame.transform.smoothscale(
        image, (max(size[0], round(width * factor)), max(size[1], round(height * factor)))
    )
    crop = pygame.Rect((0, 0), size)
    crop.center = scaled.get_rect().center
    return scaled.subsurface(crop).copy()


def frame(screen: pygame.Surface, image: pygame.Surface, rect: pygame.Rect) -> None:
    """Hang a painting in a thin gilt frame."""
    screen.blit(image, rect)
    pygame.draw.rect(screen, (26, 15, 18), rect.inflate(6, 6), 3)
    pygame.draw.rect(screen, (149, 111, 61), rect.inflate(2, 2), 1)
