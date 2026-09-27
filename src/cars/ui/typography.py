"""The bundled typefaces: Source Sans 3 for text and figures, Source Serif 4 for titles.

Both are Adobe's open-source families under the SIL Open Font License (see
``content/fonts/OFL.txt``). Bundling them means the game looks the same on every
machine. A typeface choice pairs a face for running text with one for titles.
"""

from typing import NamedTuple

import pygame

from cars.paths import content_path

TEXT, TITLE = "text", "title"


class Face(NamedTuple):
    """The files of one family: regular, bold and italic."""

    regular: str
    bold: str
    italic: str


SANS = Face("SourceSans3-Regular.ttf", "SourceSans3-Semibold.ttf", "SourceSans3-It.ttf")
SERIF = Face("SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf")

# (name, text face, title face): Modern is sans with serif titles, Classic all serif, Plain all sans.
FONT_CHOICES = [
    ("Modern", SANS, SERIF),
    ("Classic", SERIF, SERIF),
    ("Plain", SANS, SANS),
]
DEFAULT_FONT = 0


def load_font(
    index: int, size: int, role: str = TEXT, bold: bool = False, italic: bool = False
) -> pygame.font.Font:
    """The typeface choice ``index`` at ``size`` pixels, for running text or for titles."""
    _, text, title = FONT_CHOICES[index]
    face = title if role == TITLE else text
    name = face.italic if italic else face.bold if bold else face.regular
    font = pygame.font.Font(content_path("fonts", name), size)
    if bold and italic:
        font.bold = True
    return font
