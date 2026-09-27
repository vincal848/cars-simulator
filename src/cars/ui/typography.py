"""Historical serif faces with portable fallbacks. System fonts are not redistributed."""

import pygame

FONT_CHOICES = [
    ("Palatino", "palatinolinotype,bookantiqua,dejavuserif"),
    ("Garamond", "garamond,georgia,dejavuserif"),
    ("Baskerville", "baskervilleoldface,georgia,dejavuserif"),
]
DEFAULT_FONT = 1


def system_font(index: int, size: int, italic: bool = False, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont(FONT_CHOICES[index][1], size, bold=bold, italic=italic)
