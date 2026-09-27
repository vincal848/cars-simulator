"""Army markers: one plate per stack, in the owner's colour.

A plate carries a NATO-style symbol for the leading unit's arm and the number
of units in the stack, with a strength bar beneath. Zoomed in, the leading
unit's figure stands on the plate; zoomed out, the plate alone keeps busy
frontiers readable.
"""

from functools import lru_cache

import pygame

from cars.sim.entities import AIR, ARTILLERY, CAVALRY, FLEET, INFANTRY, SCOUT
from cars.ui.palette import GOLD, PAPER, ROUTE_GOLD

PLATE_SIZE = (40, 19)
SYMBOL_SIZE = (15, 11)
EDGE = (26, 15, 18)
BAR_BACK = (25, 35, 38)
HEALTHY, WOUNDED, BROKEN = (145, 211, 151), (231, 190, 96), (236, 120, 96)
OUT_OF_SUPPLY = (236, 110, 84)


def draw_army(
    screen: pygame.Surface,
    center: tuple[float, float],
    color,
    kind: str,
    count: int,
    strength: float,
    font: pygame.font.Font,
    selected: bool = False,
    supplied: bool = True,
    regional: bool = False,
) -> pygame.Rect:
    """Draw a stack's plate centred on ``center``; ``strength`` is from 0 to 1. Returns its rect."""
    x, y = round(center[0]), round(center[1])
    plate = _plate(tuple(color), kind, count, selected, regional, font)
    rect = plate.get_rect(center=(x, y))
    screen.blit(plate, rect)
    bar = pygame.Rect(rect.x + 3, rect.bottom + 1, rect.width - 6, 3)
    pygame.draw.rect(screen, BAR_BACK, bar)
    fill = HEALTHY if strength > 0.6 else WOUNDED if strength > 0.3 else BROKEN
    pygame.draw.rect(screen, fill, (bar.x, bar.y, round(bar.width * max(0, min(1, strength))), bar.height))
    if not supplied:
        pygame.draw.circle(screen, EDGE, (rect.right, rect.top), 6)
        pygame.draw.circle(screen, OUT_OF_SUPPLY, (rect.right, rect.top), 5)
        pygame.draw.line(screen, PAPER, (rect.right, rect.top - 3), (rect.right, rect.top + 1), 2)
        pygame.draw.circle(screen, PAPER, (rect.right, rect.top + 3), 1)
    return rect


@lru_cache(maxsize=512)
def _plate(color, kind: str, count: int, selected: bool, regional: bool, font) -> pygame.Surface:
    width, height = PLATE_SIZE
    surface = pygame.Surface((width + 4, height + 4), pygame.SRCALPHA)
    body = pygame.Rect(2, 2, width, height)
    shadow = body.move(1, 2)
    pygame.draw.rect(surface, (0, 0, 0, 110), shadow, border_radius=4)
    pygame.draw.rect(surface, _shade(color, 0.78), body, border_radius=4)
    pygame.draw.line(surface, _shade(color, 1.1), (body.x + 3, body.y + 1), (body.right - 4, body.y + 1))
    pygame.draw.rect(surface, ROUTE_GOLD if selected else EDGE, body, 2 if selected else 1, border_radius=4)
    symbol = pygame.Rect(body.x + 4, body.centery - SYMBOL_SIZE[1] // 2, *SYMBOL_SIZE)
    _draw_symbol(surface, kind, symbol)
    label = font.render(str(count), True, PAPER)
    surface.blit(label, label.get_rect(midleft=(symbol.right + 4, body.centery)))
    if regional:
        pygame.draw.polygon(
            surface,
            GOLD,
            [(body.x, body.y + 3), (body.x + 3, body.y), (body.x + 6, body.y + 3), (body.x + 3, body.y + 6)],
        )
    return surface


def _draw_symbol(surface: pygame.Surface, kind: str, box: pygame.Rect) -> None:
    """The arm of service, after the NATO map symbols the period's staff maps anticipated."""
    ink = PAPER
    pygame.draw.rect(surface, EDGE, box.inflate(2, 2))
    pygame.draw.rect(surface, ink, box, 1)
    left, top, right, bottom = box.left + 1, box.top + 1, box.right - 2, box.bottom - 2
    if kind == INFANTRY:
        pygame.draw.line(surface, ink, (left, top), (right, bottom))
        pygame.draw.line(surface, ink, (left, bottom), (right, top))
    elif kind == CAVALRY:
        pygame.draw.line(surface, ink, (left, bottom), (right, top))
    elif kind == SCOUT:
        pygame.draw.line(surface, ink, (left, bottom), (right, top))
        pygame.draw.line(surface, ink, (box.centerx, top), (box.centerx, bottom))
    elif kind == ARTILLERY:
        pygame.draw.circle(surface, ink, box.center, 2)
    elif kind == FLEET:
        # A hull on the water.
        pygame.draw.polygon(
            surface,
            ink,
            [(left + 1, box.centery), (right - 1, box.centery), (right - 3, bottom), (left + 3, bottom)],
        )
        pygame.draw.line(surface, ink, (box.centerx, top + 1), (box.centerx, box.centery), 1)
    elif kind == AIR:
        # Two propeller blades.
        pygame.draw.ellipse(surface, ink, (left + 1, box.centery - 2, box.width // 2 - 2, 4), 1)
        pygame.draw.ellipse(surface, ink, (box.centerx, box.centery - 2, box.width // 2 - 2, 4), 1)


def _shade(color, factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)
