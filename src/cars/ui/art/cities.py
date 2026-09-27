"""Regional settlement silhouettes and the one-point city pin.

Each regional building style gets its own skyline. Sprites are drawn
on a 48x40 design grid at three times resolution.
"""

import math

import pygame

SCALE = 3
PIN_RADIUS = 11
PIN_OUTLINE = (34, 27, 27)

_sprites: dict[str, pygame.Surface] = {}


class _Pen:
    """Draws in design-grid units on a supersampled surface."""

    def __init__(self, surface: pygame.Surface) -> None:
        self.s = surface

    def poly(self, points, color) -> None:
        pygame.draw.polygon(self.s, color, [(int(x * SCALE), int(y * SCALE)) for x, y in points])

    def rect(self, x, y, w, h, color) -> None:
        pygame.draw.rect(self.s, color, (x * SCALE, y * SCALE, w * SCALE, h * SCALE))

    def line(self, a, b, color, width=1) -> None:
        start = tuple(int(v * SCALE) for v in a)
        end = tuple(int(v * SCALE) for v in b)
        pygame.draw.line(self.s, color, start, end, max(1, int(width * SCALE)))

    def house(self, x, y, w, h, wall, roof, flat=False) -> None:
        self.rect(x, y, w, h, wall)
        self.rect(x + w * 0.72, y, w * 0.28, h, tuple(int(c * 0.73) for c in wall))
        if flat:
            self.rect(x - 1, y - 2, w + 2, 3, roof)
        else:
            self.poly([(x - 2, y), (x + w * 0.45, y - 7), (x + w + 2, y)], roof)
        self.rect(x + w * 0.4, y + h - 5, 3, 5, (62, 51, 40))
        self.rect(x + 2, y + 3, 2, 3, (238, 208, 133))


def city_sprite(style: str) -> pygame.Surface:
    if style not in _sprites:
        surface = pygame.Surface((144, 120), pygame.SRCALPHA)
        pen = _Pen(surface)
        skyline, foreground = _STYLES.get(style, (_capital_skyline, _capital_foreground))
        skyline(pen)
        foreground(pen)
        _sprites[style] = surface
    return _sprites[style]


def draw_pin(screen: pygame.Surface, point, color, hovered: bool = False) -> pygame.Rect:
    """A compact objective seal centred on the settlement."""
    cx, cy = point
    center = (int(cx), int(cy))
    pygame.draw.circle(screen, PIN_OUTLINE, center, PIN_RADIUS)
    pygame.draw.circle(screen, tuple(int(v * 0.75) for v in color), center, 9)
    pygame.draw.circle(screen, (250, 221, 147) if hovered else (211, 175, 103), center, PIN_RADIUS, 2)
    star = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        radius = 6 if i % 2 == 0 else 2.6
        star.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
    pygame.draw.polygon(screen, (252, 231, 173), star)
    return pygame.Rect(cx - PIN_RADIUS, cy - PIN_RADIUS, PIN_RADIUS * 2, PIN_RADIUS * 2)


# Skylines ---------------------------------------------------------------------------


def _northern_skyline(pen: _Pen) -> None:
    for x, y in ((4, 22), (17, 18), (31, 24)):
        pen.house(x, y, 12, 12, (150, 113, 71), (70, 88, 84))
        for yy in range(y + 3, y + 12, 3):
            pen.line((x, yy), (x + 11, yy), (98, 73, 47), 0.5)
    pen.rect(20, 7, 5, 11, (133, 113, 85))
    pen.poly([(18, 7), (22, 2), (27, 7)], (63, 77, 74))


def _atlantic_skyline(pen: _Pen) -> None:
    pen.house(3, 24, 13, 12, (168, 109, 85), (63, 83, 92))
    pen.house(29, 23, 15, 13, (174, 119, 88), (69, 80, 89))
    pen.house(17, 17, 12, 20, (209, 191, 150), (64, 77, 87))
    pen.rect(21, 7, 5, 11, (221, 202, 164))
    pen.poly([(20, 7), (23, 0), (27, 7)], (54, 65, 72))
    pen.line((23, 1), (23, -1), (205, 175, 98))


def _sierra_skyline(pen: _Pen) -> None:
    pen.house(3, 24, 17, 13, (194, 155, 101), (136, 81, 48), True)
    pen.house(28, 23, 15, 14, (213, 181, 129), (133, 80, 49), True)
    pen.house(17, 16, 12, 21, (225, 195, 143), (135, 75, 44), True)
    pen.poly([(16, 16), (23, 10), (30, 16)], (218, 188, 135))
    pen.rect(21, 16, 3, 4, (79, 59, 39))


def _caribbean_skyline(pen: _Pen) -> None:
    pen.house(2, 24, 15, 12, (197, 201, 168), (119, 75, 51))
    pen.house(18, 21, 14, 15, (228, 211, 151), (145, 83, 56))
    pen.house(33, 25, 12, 11, (143, 177, 170), (139, 80, 57))
    for x in range(18, 33, 4):
        pen.line((x, 29), (x, 36), (231, 219, 181))
    pen.line((38, 25), (38, 9), (123, 95, 63), 1.5)
    for dx, dy in ((-9, -3), (-6, -7), (7, -6), (10, -1)):
        pen.line((38, 10), (38 + dx, 10 + dy), (63, 114, 75), 2)


def _andean_skyline(pen: _Pen) -> None:
    pen.poly([(3, 37), (9, 31), (42, 31), (46, 37)], (151, 134, 96))
    pen.poly([(9, 30), (14, 25), (38, 25), (42, 30)], (164, 147, 107))
    pen.house(9, 22, 13, 10, (172, 157, 121), (138, 83, 53))
    pen.house(27, 19, 13, 13, (197, 177, 137), (141, 79, 50))
    pen.house(20, 10, 7, 16, (177, 161, 125), (101, 70, 48), True)


def _amazon_skyline(pen: _Pen) -> None:
    for x, y in ((4, 19), (19, 16), (33, 21)):
        for post in (x + 2, x + 10):
            pen.line((post, y + 10), (post, 37), (94, 74, 47), 1.3)
        pen.house(x, y, 12, 10, (159, 123, 75), (116, 107, 56))
    pen.line((2, 37), (45, 37), (151, 128, 79), 2)
    for x in (8, 22, 36):
        pen.line((x, 37), (x, 40), (98, 91, 61), 1)


def _southern_skyline(pen: _Pen) -> None:
    pen.house(4, 25, 21, 11, (216, 200, 155), (134, 78, 58))
    pen.house(27, 21, 15, 15, (202, 187, 145), (147, 79, 58))
    for x in range(6, 27, 5):
        pen.line((x, 27), (x, 36), (246, 223, 172), 1)
    pen.line((4, 27), (26, 27), (160, 108, 71), 2)
    pen.rect(35, 13, 3, 8, (178, 159, 121))


def _capital_skyline(pen: _Pen) -> None:
    pen.house(4, 23, 14, 13, (158, 164, 146), (71, 91, 91))
    pen.house(18, 20, 13, 16, (185, 178, 149), (73, 87, 88))
    pen.house(31, 25, 13, 11, (163, 162, 142), (70, 90, 88))
    pen.house(23, 7, 6, 15, (216, 207, 172), (68, 85, 85))
    pen.rect(24, 11, 4, 3, (227, 189, 100))
    pen.line((2, 37), (46, 37), (107, 96, 69), 2)


# Foregrounds: walls, quays and fences in front of each skyline ------------------------


def _northern_foreground(pen: _Pen) -> None:
    for x in range(2, 47, 4):
        pen.line((x, 32), (x, 39), (107, 77, 45), 1.5)
        pen.poly([(x - 1, 32), (x, 29), (x + 1, 32)], (159, 123, 73))
    pen.line((1, 35), (47, 35), (188, 147, 89), 1)


def _atlantic_foreground(pen: _Pen) -> None:
    for x in (2, 40):
        pen.rect(x, 25, 6, 13, (154, 151, 125))
        for dx in (0, 2, 4):
            pen.rect(x + dx, 23, 1.5, 3, (199, 185, 145))
    pen.line((7, 37), (40, 37), (197, 177, 131), 2)


def _sierra_foreground(pen: _Pen) -> None:
    for x in (4, 36):
        pen.rect(x, 13, 6, 12, (214, 172, 111))
        pen.rect(x + 2, 15, 2, 4, (82, 60, 38))
        pen.poly([(x - 1, 13), (x + 3, 8), (x + 7, 13)], (155, 87, 48))
    pen.line((2, 38), (46, 38), (190, 137, 78), 2)


def _caribbean_foreground(pen: _Pen) -> None:
    pen.poly([(0, 34), (12, 32), (14, 38), (1, 39)], (167, 148, 99))
    for x in (2, 7, 12):
        pen.line((x, 34), (x, 40), (103, 77, 43), 1)
    pen.line((1, 33), (12, 33), (226, 195, 126), 1)


def _andean_foreground(pen: _Pen) -> None:
    for y, start in ((33, 6), (36, 3), (39, 0)):
        pen.line((start, y), (48 - start, y), (210, 183, 128), 1.3)
        for x in range(start + 2, 48 - start, 6):
            pen.line((x, y), (x, y + 2), (100, 93, 74), 0.5)


def _amazon_foreground(pen: _Pen) -> None:
    for x in (2, 42):
        pen.line((x, 36), (x + 1, 10), (89, 76, 41), 1.5)
        for dx, dy in ((-5, 1), (5, -3), (4, 3)):
            pen.line((x + 1, 11), (x + dx, 11 + dy), (70, 109, 59), 2)
    pen.line((4, 36), (43, 36), (196, 158, 93), 1)


def _southern_foreground(pen: _Pen) -> None:
    for x in range(1, 48, 5):
        pen.line((x, 35), (x, 40), (172, 138, 86), 1)
    pen.line((1, 37), (47, 37), (221, 189, 128), 1)
    pen.poly([(2, 26), (11, 19), (18, 26)], (159, 78, 53))


def _capital_foreground(pen: _Pen) -> None:
    pen.rect(1, 11, 5, 25, (208, 211, 189))
    pen.rect(0, 9, 7, 4, (98, 137, 136))
    pen.poly([(0, 9), (3, 5), (7, 9)], (64, 91, 96))
    pen.line((0, 37), (47, 37), (195, 181, 139), 2)


_STYLES = {
    "northern": (_northern_skyline, _northern_foreground),
    "atlantic": (_atlantic_skyline, _atlantic_foreground),
    "sierra": (_sierra_skyline, _sierra_foreground),
    "caribbean": (_caribbean_skyline, _caribbean_foreground),
    "andean": (_andean_skyline, _andean_foreground),
    "amazon": (_amazon_skyline, _amazon_foreground),
    "southern": (_southern_skyline, _southern_foreground),
}
