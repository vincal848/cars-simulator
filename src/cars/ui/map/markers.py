"""Army markers: one plate per stack, in the owner's colour.

A plate carries a NATO-style symbol for the leading unit's arm and the number
of units in the stack, with a strength bar beneath. Zoomed in, the leading
unit's figure stands on the plate; zoomed out, the plate alone keeps busy
frontiers readable. Every size is multiplied by the UI scale.
"""

from functools import lru_cache

import pygame

from cars.sim.entities import AIR, ARTILLERY, CAVALRY, FLEET, INFANTRY, SCOUT

PLATE_SIZE = (40, 19)
SYMBOL_SIZE = (15, 11)
EDGE = (26, 15, 18)
INK = (250, 238, 214)
SELECTED = (245, 207, 115)
REGIONAL = (219, 179, 91)
BAR_BACK = (25, 35, 38)
HEALTHY, WOUNDED, BROKEN = (145, 211, 151), (231, 190, 96), (236, 120, 96)
OUT_OF_SUPPLY = (236, 110, 84)


def plate_rect(center: tuple[float, float], scale: float = 1.0) -> pygame.Rect:
    """Where a plate centred on ``center`` is drawn, including its strength bar."""
    width, height = round(PLATE_SIZE[0] * scale), round((PLATE_SIZE[1] + 5) * scale)
    return pygame.Rect(
        round(center[0] - width / 2), round(center[1] - PLATE_SIZE[1] * scale / 2), width, height
    )


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
    scale: float = 1.0,
) -> pygame.Rect:
    """Draw a stack's plate centred on ``center``; ``strength`` is from 0 to 1. Returns its rect."""
    x, y = round(center[0]), round(center[1])
    plate = _plate(tuple(color), kind, count, selected, regional, font, scale)
    rect = plate.get_rect(center=(x, y))
    screen.blit(plate, rect)
    pad = round(3 * scale)
    bar = pygame.Rect(rect.x + pad, rect.bottom, rect.width - pad * 2, max(2, round(3 * scale)))
    pygame.draw.rect(screen, BAR_BACK, bar)
    fill = HEALTHY if strength > 0.6 else WOUNDED if strength > 0.3 else BROKEN
    pygame.draw.rect(screen, fill, (bar.x, bar.y, round(bar.width * max(0, min(1, strength))), bar.height))
    if not supplied:
        radius = round(6 * scale)
        spot = (rect.right - pad, rect.top + pad)
        pygame.draw.circle(screen, EDGE, spot, radius)
        pygame.draw.circle(screen, OUT_OF_SUPPLY, spot, radius - 1)
        pygame.draw.line(
            screen, INK, (spot[0], spot[1] - radius // 2), (spot[0], spot[1] + 1), max(1, round(2 * scale))
        )
        pygame.draw.circle(screen, INK, (spot[0], spot[1] + radius // 2), max(1, round(scale)))
    return rect


@lru_cache(maxsize=512)
def _plate(
    color, kind: str, count: int, selected: bool, regional: bool, font, scale: float
) -> pygame.Surface:
    width, height = round(PLATE_SIZE[0] * scale), round(PLATE_SIZE[1] * scale)
    margin = round(2 * scale)
    surface = pygame.Surface((width + margin * 2, height + margin * 2), pygame.SRCALPHA)
    body = pygame.Rect(margin, margin, width, height)
    radius = round(4 * scale)
    pygame.draw.rect(surface, (0, 0, 0, 110), body.move(1, margin), border_radius=radius)
    pygame.draw.rect(surface, _shade(color, 0.78), body, border_radius=radius)
    pygame.draw.line(
        surface, _shade(color, 1.1), (body.x + radius, body.y + 1), (body.right - radius, body.y + 1)
    )
    border = max(1, round((2 if selected else 1) * scale))
    pygame.draw.rect(surface, SELECTED if selected else EDGE, body, border, border_radius=radius)
    symbol_size = (round(SYMBOL_SIZE[0] * scale), round(SYMBOL_SIZE[1] * scale))
    symbol = pygame.Rect(body.x + round(4 * scale), body.centery - symbol_size[1] // 2, *symbol_size)
    _draw_symbol(surface, kind, symbol, max(1, round(scale)))
    label = font.render(str(count), True, INK)
    surface.blit(label, label.get_rect(midleft=(symbol.right + round(4 * scale), body.centery)))
    if regional:
        d = round(3 * scale)
        x, y = body.x + d, body.y + d
        pygame.draw.polygon(surface, REGIONAL, [(x - d, y), (x, y - d), (x + d, y), (x, y + d)])
    return surface


def _draw_symbol(surface: pygame.Surface, kind: str, box: pygame.Rect, line: int) -> None:
    """The arm of service, drawn as a NATO-style map symbol."""
    pygame.draw.rect(surface, EDGE, box.inflate(2, 2))
    pygame.draw.rect(surface, INK, box, line)
    left, top, right, bottom = box.left + line, box.top + line, box.right - line - 1, box.bottom - line - 1
    if kind == INFANTRY:
        pygame.draw.line(surface, INK, (left, top), (right, bottom), line)
        pygame.draw.line(surface, INK, (left, bottom), (right, top), line)
    elif kind == CAVALRY:
        pygame.draw.line(surface, INK, (left, bottom), (right, top), line)
    elif kind == SCOUT:
        pygame.draw.line(surface, INK, (left, bottom), (right, top), line)
        pygame.draw.line(surface, INK, (box.centerx, top), (box.centerx, bottom), line)
    elif kind == ARTILLERY:
        pygame.draw.circle(surface, INK, box.center, max(2, box.height // 5))
    elif kind == FLEET:
        # A hull on the water.
        middle = box.centery
        hull = [
            (left + 1, middle),
            (right - 1, middle),
            (right - 3 * line, bottom),
            (left + 3 * line, bottom),
        ]
        pygame.draw.polygon(surface, INK, hull)
        pygame.draw.line(surface, INK, (box.centerx, top + line), (box.centerx, middle), line)
    elif kind == AIR:
        # Two propeller blades.
        half = box.width // 2 - 2 * line
        blade = max(3, box.height // 3)
        pygame.draw.ellipse(surface, INK, (left + line, box.centery - blade // 2, half, blade), line)
        pygame.draw.ellipse(surface, INK, (box.centerx, box.centery - blade // 2, half, blade), line)


def _shade(color, factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)
