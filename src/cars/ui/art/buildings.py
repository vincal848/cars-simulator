"""Animated miniature buildings. Purely cosmetic: animation never affects the simulation."""

import math

import pygame

from cars.ui.art.lighting import contact_shadow

TILE = 80
STONE = (192, 173, 136)
ROOF = (116, 47, 43)
GILT = (220, 181, 93)


def draw_building(
    screen: pygame.Surface, kind: str, center, size: int, time: float, active: bool = True
) -> None:
    """Draw building ``kind`` centred on ``center``; inactive (unbuilt) ones are faded."""
    contact_shadow(screen, (center[0] + 2, center[1] + size * 0.28), (size, int(size * 0.4)))
    tile = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    if not active:
        time = 0
    pygame.draw.ellipse(tile, (20, 27, 24, 110), (8, 58, 65, 13))
    _DRAWERS.get(kind, _mine)(tile, time, active)
    if not active:
        tile.set_alpha(130)
    icon = pygame.transform.smoothscale(tile, (size, size))
    screen.blit(icon, icon.get_rect(center=center))


def _farm(tile, time, active) -> None:
    pygame.draw.polygon(tile, (140, 139, 67), [(4, 53), (42, 45), (77, 59), (38, 73)])
    for i in range(6):
        x = 12 + i * 10
        y = 57 + (i % 2) * 5
        sway = math.sin(time * 2 + i) * 2 if active else 0
        pygame.draw.line(tile, GILT, (x, y + 7), (x + sway, y - 3), 2)
        pygame.draw.line(tile, GILT, (x + sway, y), (x + sway - 3, y - 3), 2)
    pygame.draw.rect(tile, STONE, (25, 30, 32, 27))
    pygame.draw.polygon(tile, ROOF, [(20, 32), (40, 15), (62, 32)])
    pygame.draw.rect(tile, (57, 46, 37), (36, 41, 9, 16))
    pygame.draw.rect(tile, GILT, (28, 36, 6, 6))


def _lumber_mill(tile, time, _active) -> None:
    pygame.draw.polygon(tile, STONE, [(29, 19), (48, 19), (55, 63), (23, 63)])
    pygame.draw.polygon(tile, ROOF, [(25, 21), (39, 10), (52, 21)])
    pygame.draw.rect(tile, (63, 46, 32), (33, 49, 10, 14))
    angle = time * 0.8
    for i in range(4):
        a = angle + i * math.pi / 2

        def point(radius, side, a=a):
            return (
                39 + math.cos(a) * radius - math.sin(a) * side,
                34 + math.sin(a) * radius + math.cos(a) * side,
            )

        pygame.draw.line(tile, (70, 49, 33), (39, 34), point(30, 0), 2)
        pygame.draw.polygon(tile, (226, 212, 166), [point(9, 1), point(29, 1), point(29, 7), point(9, 4)])
    pygame.draw.circle(tile, GILT, (39, 34), 4)
    for y in (64, 68):
        pygame.draw.line(tile, (128, 82, 45), (52, y), (72, y), 4)


def _roads(tile, _time, _active) -> None:
    points = [(15, 76), (29, 54), (49, 40), (46, 11)]
    pygame.draw.lines(tile, (77, 64, 46), False, points, 16)
    pygame.draw.lines(tile, (205, 181, 128), False, points, 11)
    for x, y in ((20, 55), (57, 32), (36, 16)):
        pygame.draw.rect(tile, STONE, (x, y, 5, 12))


def _shipyard(tile, time, _active) -> None:
    pygame.draw.ellipse(tile, (62, 114, 137), (5, 46, 70, 25))
    for y in (51, 59, 67):
        pygame.draw.line(tile, (116, 158, 171), (9, y), (70, y), 1)
    pygame.draw.polygon(tile, ROOF, [(15, 46), (65, 46), (55, 60), (27, 60)])
    pygame.draw.rect(tile, STONE, (31, 34, 20, 12))
    pygame.draw.lines(tile, GILT, False, [(17, 51), (17, 15), (56, 15), (56, 34)], 4)
    pygame.draw.line(tile, STONE, (56, 30), (56, 38 + int(3 * math.sin(time))), 2)


def _gasworks(tile, time, _active) -> None:
    # A gasholder beside the retort house, its bell rising and falling.
    lift = int(3 * math.sin(time))
    pygame.draw.rect(tile, (72, 76, 80), (38, 30 + lift, 34, 38 - lift))
    pygame.draw.ellipse(tile, (98, 104, 108), (38, 25 + lift, 34, 10))
    for x in (38, 49, 60, 71):
        pygame.draw.line(tile, STONE, (x, 22), (x, 70), 2)
    pygame.draw.line(tile, STONE, (37, 22), (72, 22), 2)
    pygame.draw.rect(tile, STONE, (6, 40, 30, 30))
    pygame.draw.polygon(tile, ROOF, [(3, 41), (21, 27), (39, 41)])
    pygame.draw.rect(tile, (60, 52, 46), (12, 12, 6, 22))


def _mine(tile, time, active) -> None:
    pygame.draw.polygon(tile, (106, 119, 116), [(8, 64), (20, 32), (37, 18), (55, 35), (73, 64)])
    pygame.draw.rect(tile, (28, 31, 31), (28, 39, 27, 26))
    pygame.draw.lines(tile, (157, 108, 61), False, [(26, 65), (26, 37), (57, 37), (57, 65)], 5)
    pygame.draw.line(tile, GILT, (36, 39), (36, 47), 2)
    pygame.draw.circle(tile, (244, 201, 104), (36, 48), 3)
    offset = math.sin(time * 1.4) * 8 if active else 0
    pygame.draw.line(tile, (139, 136, 117), (16, 70), (73, 70), 2)
    pygame.draw.rect(tile, (104, 118, 125), (39 + offset, 55, 20, 11))
    for x in (43, 55):
        pygame.draw.circle(tile, (38, 34, 31), (int(x + offset), 67), 3)


_DRAWERS = {
    "farm": _farm,
    "lumber_mill": _lumber_mill,
    "roads": _roads,
    "shipyard": _shipyard,
    "gasworks": _gasworks,
    "mine": _mine,
}


def celebration(screen: pygame.Surface, center, age: float) -> None:
    """Expanding ring and sparks for two seconds after construction."""
    if not 0 <= age <= 2:
        return
    layer = pygame.Surface((140, 140), pygame.SRCALPHA)
    alpha = int(220 * (1 - age / 2))
    pygame.draw.circle(layer, (239, 205, 125, alpha), (70, 70), int(12 + age * 25), 2)
    for i in range(12):
        a = i * math.tau / 12
        radius = 10 + age * 28
        x, y = 70 + math.cos(a) * radius, 70 + math.sin(a) * radius - age * 12
        pygame.draw.circle(layer, (247, 223, 160, alpha), (int(x), int(y)), 2)
    screen.blit(layer, (center[0] - 70, center[1] - 70))
