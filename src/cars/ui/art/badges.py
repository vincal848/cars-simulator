"""Engraved circular insignia for buttons and headings, cached per kind and size."""

from functools import lru_cache

import pygame

CANVAS = 128
GILT = (222, 183, 101)
HIGHLIGHT = (250, 222, 163)
RIM = (110, 74, 43)


@lru_cache(maxsize=128)
def badge(kind: str, size: int = 28) -> pygame.Surface:
    s = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    pygame.draw.circle(s, (15, 13, 19, 170), (66, 68), 59)
    pygame.draw.circle(s, RIM, (64, 64), 58)
    pygame.draw.circle(s, (65, 24, 36), (64, 64), 54)
    pygame.draw.circle(s, GILT, (64, 64), 52, 2)
    pygame.draw.arc(s, HIGHLIGHT, (8, 8, 112, 112), 0.3, 2.9, 3)
    _EMBLEMS.get(kind, _document)(s)
    return pygame.transform.smoothscale(s, (size, size))


def _line(s, a, b, width=5) -> None:
    pygame.draw.line(s, GILT, a, b, width)


def _poly(s, points) -> None:
    pygame.draw.polygon(s, GILT, points)


def _crossed_swords(s) -> None:
    for flip in (False, True):

        def p(x, y, flip=flip):
            return (128 - x, y) if flip else (x, y)

        _poly(s, [p(35, 26), p(43, 31), p(88, 88), p(80, 94)])
        _line(s, p(64, 86), p(89, 67), 5)
        _line(s, p(79, 87), p(96, 107), 6)


def _anchor(s) -> None:
    pygame.draw.circle(s, GILT, (64, 32), 10, 4)
    _line(s, (64, 42), (64, 98))
    _line(s, (38, 55), (90, 55))
    pygame.draw.arc(s, GILT, (28, 50, 72, 50), 3.14, 6.28, 6)
    _poly(s, [(26, 69), (43, 79), (28, 88)])
    _poly(s, [(102, 69), (85, 79), (100, 88)])


def _aircraft(s) -> None:
    _poly(s, [
        (64, 28), (70, 49), (102, 43), (91, 58), (71, 66), (77, 91),
        (64, 82), (51, 91), (57, 66), (37, 58), (26, 43), (58, 49),
    ])  # fmt: skip


def _wagon(s) -> None:
    pygame.draw.rect(s, GILT, (31, 42, 63, 39), 4)
    _line(s, (52, 44), (52, 79), 3)
    _line(s, (74, 44), (74, 79), 3)
    for x in (43, 84):
        pygame.draw.circle(s, GILT, (x, 90), 9, 4)


def _bridge(s) -> None:
    pygame.draw.arc(s, GILT, (27, 32, 74, 73), 0, 3.14, 7)
    _line(s, (27, 68), (27, 95))
    _line(s, (101, 68), (101, 95))
    _line(s, (22, 94), (106, 94))
    for x in (44, 64, 84):
        _line(s, (x, 40), (x, 64), 3)


def _wheat(s) -> None:
    _line(s, (62, 100), (66, 30), 4)
    for y in (34, 48, 62, 76):
        _poly(s, [(64, y + 13), (40, y + 2), (40, y - 7), (63, y)])
        _poly(s, [(66, y + 13), (89, y + 2), (89, y - 7), (67, y)])


def _castle(s) -> None:
    pygame.draw.rect(s, GILT, (33, 49, 63, 47), 4)
    for x in (34, 58, 82):
        pygame.draw.rect(s, GILT, (x, 34, 13, 18))
    pygame.draw.rect(s, GILT, (58, 70, 14, 26))


def _people(s) -> None:
    for x, y in ((43, 49), (85, 49), (64, 39)):
        pygame.draw.circle(s, GILT, (x, y), 9)
        pygame.draw.arc(s, GILT, (x - 15, y + 10, 30, 41), 0, 3.14, 8)
    _line(s, (31, 92), (97, 92), 4)


def _globe(s) -> None:
    pygame.draw.circle(s, GILT, (64, 64), 35, 3)
    pygame.draw.ellipse(s, GILT, (49, 29, 30, 70), 3)
    _line(s, (29, 64), (99, 64), 3)


def _coin(s) -> None:
    pygame.draw.circle(s, GILT, (64, 64), 31, 5)
    _line(s, (64, 39), (64, 89), 4)
    _line(s, (48, 50), (80, 50), 4)
    _line(s, (48, 76), (80, 76), 4)


def _clock(s) -> None:
    pygame.draw.circle(s, GILT, (64, 64), 31, 5)
    _line(s, (64, 64), (64, 41), 4)
    _line(s, (64, 64), (82, 75), 4)


def _gear(s) -> None:
    pygame.draw.circle(s, GILT, (64, 64), 23, 7)
    pygame.draw.circle(s, HIGHLIGHT, (64, 64), 7)
    for a, b in [((64, 25), (64, 43)), ((64, 85), (64, 103)), ((25, 64), (43, 64)), ((85, 64), (103, 64))]:
        _line(s, a, b, 9)


def _document(s) -> None:
    pygame.draw.rect(s, GILT, (35, 29, 59, 70), 4)
    for y in (45, 60, 75):
        _line(s, (47, y), (82, y), 3)
    _poly(s, [(79, 83), (105, 90), (95, 111), (80, 101)])


_EMBLEMS = {
    "land": _crossed_swords,
    "recruit": _crossed_swords,
    "naval": _anchor,
    "air": _aircraft,
    "supply": _wagon,
    "ready": _wagon,
    "infrastructure": _bridge,
    "build": _wheat,
    "province": _castle,
    "industry": _castle,
    "population": _people,
    "home": _globe,
    "terrain": _globe,
    "gold": _coin,
    "end": _clock,
    "settings": _gear,
}
