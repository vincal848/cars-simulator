"""Unit sprites. Land regiments wear their faction's regional dress; roles share
silhouettes, and no culture carries a stat bonus."""

import math

import pygame

from cars.paths import load_content
from cars.sim.entities import AIR, ARTILLERY, CAVALRY, FLEET, LAND_KINDS, SCOUT

UNIFORMS: dict[str, dict] = load_content("gfx", "uniform_styles.json")
DEFAULT_UNIFORM = "northern"
SCALE = 3
SPRITE_SIZE = (36, 40)
INK = (231, 233, 209)
SKIN = (186, 147, 103)
HANDS = (173, 135, 96)


class UnitSprites:
    """Sprites cached by (kind, faction colour, uniform style)."""

    def __init__(self) -> None:
        self._cache: dict[tuple, pygame.Surface] = {}

    def sprite(self, kind: str, color, style: str = DEFAULT_UNIFORM) -> pygame.Surface:
        key = (kind, tuple(color), style)
        if key not in self._cache:
            if kind in LAND_KINDS:
                self._cache[key] = regiment(kind, color, style)
            else:
                self._cache[key] = _vessel(kind, color)
        return self._cache[key]


def _vessel(kind: str, color) -> pygame.Surface:
    s = pygame.Surface(SPRITE_SIZE, pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 80), (3, 30, 30, 8))
    if kind == FLEET:
        pygame.draw.polygon(s, color, [(2, 24), (34, 24), (27, 32), (9, 32)])
        pygame.draw.rect(s, INK, (12, 17, 13, 7))
        pygame.draw.line(s, INK, (18, 8), (18, 24), 2)
        pygame.draw.polygon(s, color, [(19, 9), (29, 13), (19, 16)])
    elif kind == AIR:
        airframe = [
            (18, 3), (22, 17), (34, 24), (33, 27), (21, 24), (22, 33), (27, 36),
            (9, 36), (14, 32), (15, 24), (3, 27), (2, 24), (14, 17),
        ]  # fmt: skip
        pygame.draw.polygon(s, INK, airframe)
        pygame.draw.line(s, color, (18, 12), (18, 29), 3)
    return s


class _Figure:
    """Draws one soldier in design units on a 48x48 grid, supersampled three times."""

    def __init__(self, surface: pygame.Surface, uniform: dict, color) -> None:
        self.s = surface
        self.uniform = uniform
        self.color = color
        self.cloth = uniform["cloth"]
        self.trim = uniform["trim"]
        self.dark = tuple(int(c * 0.55) for c in self.cloth)

    def poly(self, points, ink) -> None:
        pygame.draw.polygon(self.s, ink, [(int(x * SCALE), int(y * SCALE)) for x, y in points])

    def line(self, a, b, ink, width=1) -> None:
        start = tuple(int(v * SCALE) for v in a)
        end = tuple(int(v * SCALE) for v in b)
        pygame.draw.line(self.s, ink, start, end, max(1, int(width * SCALE)))

    def ellipse(self, rect, ink) -> None:
        pygame.draw.ellipse(self.s, ink, pygame.Rect(*(int(v * SCALE) for v in rect)))

    def soldier(self, x: float, y: float, scout: bool = False, rider: bool = False) -> None:
        """Body origin is at the shoulders; light falls from the upper left."""
        cloth, dark, trim = self.cloth, self.dark, self.trim
        coat = self.uniform["coat"]
        if not rider:
            for dx in (-3, 3):
                self.poly(
                    [(x + dx - 2, y + 10), (x + dx + 2, y + 10), (x + dx + 2, y + 23), (x + dx - 2, y + 23)],
                    dark,
                )
                self.line((x + dx - 2, y + 23), (x + dx + 3, y + 23), (35, 32, 28), 2.5)
        self.poly([(x - 6, y), (x + 5, y), (x + 7, y + 12), (x - 6, y + 13)], cloth)
        self.poly([(x + 2, y), (x + 5, y), (x + 7, y + 12), (x + 2, y + 12)], dark)
        if coat in ("long", "tails"):
            skirt = [
                (x - 6, y + 8),
                (x + 5, y + 8),
                (x + 8, y + 19),
                (x + 1, y + 17),
                (x, y + 13),
                (x - 2, y + 18),
                (x - 8, y + 19),
            ]
            self.poly(skirt, cloth)
            self.line((x - 6, y + 10), (x - 7, y + 17), trim, 0.7)
        if coat == "poncho" or scout:
            self.poly(
                [(x - 3, y - 1), (x + 3, y - 1), (x + 10, y + 12), (x, y + 18), (x - 10, y + 12)], cloth
            )
            for offset in (6, 9, 12):
                self.line((x - 6, y + offset), (x + 6, y + offset), trim, 0.8)
        else:
            self.line((x - 4, y), (x + 4, y + 11), trim, 1.5)
            self.line((x + 4, y), (x - 4, y + 11), trim, 1.5)
            for yy in (4, 7, 10):
                self.ellipse((x - 0.6, y + yy, 1.2, 1.2), (226, 192, 103))
        self.line((x - 6, y + 2), (x - 8, y + 11), cloth, 3)
        self.line((x + 6, y + 2), (x + 8, y + 10), dark, 3)
        self.ellipse((x - 9, y + 10, 3, 3), HANDS)
        self.ellipse((x + 7, y + 9, 3, 3), HANDS)
        self.poly([(x - 6, y + 1), (x - 3, y + 1), (x - 3, y + 4), (x - 6, y + 4)], self.color)
        self.ellipse((x - 3.5, y - 7, 7, 8), SKIN)
        self.poly([(x + 1, y - 5), (x + 4, y - 5), (x + 3, y), (x, y)], (131, 99, 71))
        self.hat(x, y, "hood" if scout else self.uniform["hat"])
        if rider:
            self.line((x + 8, y + 10), (x + 14, y - 3), (210, 205, 171), 1.2)
        else:
            # A long wood-stock musket; scouts carry a short carbine.
            muzzle = (x + 11, y - 6 if scout else y - 15)
            self.line((x + 5, y + 17), muzzle, (48, 46, 40), 1.5)
            self.line((x + 5, y + 17), (x + 9, y + 3), (116, 77, 43), 2.4)
            self.line((x + 10, y - 3), muzzle, (186, 185, 157), 0.6)

    def hat(self, x: float, y: float, hat: str) -> None:
        cloth, dark, trim, color = self.cloth, self.dark, self.trim, self.color
        if hat == "tricorn":
            self.poly(
                [(x - 7, y - 8), (x - 4, y - 12), (x, y - 9), (x + 5, y - 12), (x + 7, y - 7), (x, y - 5)],
                (39, 38, 34),
            )
            self.line((x - 6, y - 8), (x, y - 6), trim, 0.8)
            self.line((x, y - 6), (x + 6, y - 8), trim, 0.8)
            self.line((x + 4, y - 10), (x + 5, y - 16), color, 1.5)
        elif hat == "fur":
            self.ellipse((x - 5, y - 13, 10, 8), (66, 57, 46))
            for dx in range(-4, 5, 2):
                self.line((x + dx, y - 11), (x + dx + 1, y - 7), (118, 102, 76), 0.7)
        elif hat == "brim":
            self.poly([(x - 4, y - 12), (x + 3, y - 12), (x + 5, y - 7), (x - 5, y - 7)], dark)
            self.ellipse((x - 8, y - 8, 16, 3), trim)
        elif hat == "sailor":
            self.ellipse((x - 6, y - 11, 12, 5), trim)
            self.line((x - 4, y - 6), (x + 4, y - 6), color, 1.5)
        elif hat == "kepi":
            self.poly([(x - 4, y - 12), (x + 4, y - 11), (x + 4, y - 6), (x - 4, y - 6)], cloth)
            self.line((x - 4, y - 6), (x + 6, y - 6), (35, 35, 29), 1.5)
        elif hat == "hood":
            self.poly(
                [
                    (x - 5, y - 6),
                    (x - 5, y - 12),
                    (x, y - 15),
                    (x + 5, y - 11),
                    (x + 5, y - 5),
                    (x + 2, y - 8),
                    (x - 2, y - 8),
                ],
                dark,
            )
        else:
            self.poly([(x - 5, y - 6), (x - 4, y - 11), (x, y - 14), (x + 4, y - 11), (x + 5, y - 6)], cloth)
            self.line((x - 4, y - 8), (x + 4, y - 8), trim, 1.3)


def regiment(kind: str, color, style: str = DEFAULT_UNIFORM) -> pygame.Surface:
    uniform = UNIFORMS.get(style, UNIFORMS[DEFAULT_UNIFORM])
    surface = pygame.Surface((144, 144), pygame.SRCALPHA)
    figure = _Figure(surface, uniform, color)
    if kind == CAVALRY:
        _horse(figure)
        figure.soldier(22, 17, rider=True)
        figure.poly([(17, 30), (26, 30), (26, 36), (17, 36)], color)
        figure.line((27, 23), (36, 21), (193, 170, 119), 0.8)
    elif kind == ARTILLERY:
        figure.soldier(13, 19)
        _field_gun(figure, color)
    else:
        figure.soldier(23, 19, scout=kind == SCOUT)
    return surface


def _horse(figure: _Figure) -> None:
    figure.ellipse((9, 25, 28, 13), (114, 77, 49))
    figure.poly([(29, 29), (32, 15), (38, 13), (43, 18), (40, 23), (35, 21), (35, 32)], (130, 88, 52))
    figure.poly([(31, 16), (31, 10), (35, 15), (39, 12), (39, 17)], (58, 45, 32))
    for x in (13, 19, 30, 34):
        figure.line((x, 34), (x - 2, 44), (72, 51, 34), 2.3)
    figure.line((10, 29), (5, 37), (51, 43, 32), 2.5)


def _field_gun(figure: _Figure, color) -> None:
    figure.poly([(18, 32), (39, 33), (44, 39), (17, 39)], (122, 85, 48))
    figure.line((24, 30), (44, 23), (68, 83, 74), 5)
    figure.line((25, 28), (43, 22), (155, 155, 108), 1)
    for x in (24, 38):
        figure.ellipse((x - 5, 33, 10, 10), (50, 43, 33))
        figure.ellipse((x - 4, 34, 8, 8), (154, 116, 63))
        for angle in range(0, 360, 60):
            a = math.radians(angle)
            figure.line((x, 38), (x + 4 * math.cos(a), 38 + 4 * math.sin(a)), (67, 49, 30), 0.7)
    figure.poly([(18, 31), (22, 31), (22, 35), (18, 35)], color)
