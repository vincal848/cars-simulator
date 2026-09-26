"""Resource icons (wood, food, iron) drawn at any size."""

import pygame

from cars.ui.palette import GOLD

DESIGN_SIZE = 28


def draw_resource_icon(
    surface: pygame.Surface, kind: str, x: float, y: float, size: int = DESIGN_SIZE
) -> None:
    scale = size / DESIGN_SIZE

    def points(vertices):
        return [(x + a * scale, y + b * scale) for a, b in vertices]

    if kind == "wood":
        pygame.draw.line(surface, (181, 139, 84), points([(14, 16)])[0], points([(14, 27)])[0], 3)
        for top, base, half in [(1, 13, 7), (7, 20, 10)]:
            crown = [(14, top), (14 - half, base), (14 + half, base)]
            pygame.draw.polygon(surface, (130, 173, 133), points(crown))
            pygame.draw.lines(
                surface, (194, 205, 152), False, points([(14 - half, base), (14, top), (14 + half, base)]), 1
            )
    elif kind == "food":
        pygame.draw.line(surface, GOLD, points([(12, 27)])[0], points([(16, 2)])[0], 2)
        for i in range(4):
            yy = 5 + i * 5
            pygame.draw.polygon(
                surface, (222, 186, 99), points([(15, yy + 6), (7, yy + 2), (8, yy - 2), (15, yy + 1)])
            )
            pygame.draw.polygon(
                surface, (190, 148, 75), points([(15, yy + 5), (23, yy), (22, yy - 3), (16, yy)])
            )
    elif kind == "iron":
        pygame.draw.polygon(
            surface, (150, 172, 181), points([(2, 20), (9, 7), (21, 4), (27, 16), (22, 26), (6, 26)])
        )
        pygame.draw.polygon(surface, (203, 213, 206), points([(9, 7), (21, 4), (17, 16), (2, 20)]))
        pygame.draw.lines(surface, (63, 85, 97), False, points([(21, 4), (17, 16), (22, 26)]), 2)
