"""The Americas cartouche in the top-left corner, drawn at double size for crisp gilt."""

import pygame

from cars.ui.art.ornament import branch, fleur

SIZE = (304, 98)

NORTH_AMERICA = [
    (40, 51), (50, 37), (76, 40), (88, 49), (99, 49), (107, 58), (92, 66),
    (86, 79), (77, 83), (71, 96), (66, 94), (63, 84), (53, 77), (50, 65),
]  # fmt: skip
SOUTH_AMERICA = [
    (73, 95),
    (87, 96),
    (99, 104),
    (104, 119),
    (95, 133),
    (88, 143),
    (82, 149),
    (78, 138),
    (79, 124),
    (72, 109),
]


def americas_emblem(title_font: pygame.font.Font, subtitle_font: pygame.font.Font) -> pygame.Surface:
    s = pygame.Surface((SIZE[0] * 2, SIZE[1] * 2), pygame.SRCALPHA)
    pygame.draw.rect(s, (4, 10, 15, 115), (7, 9, 594, 182), border_radius=14)
    frame = pygame.Rect(2, 2, 588, 176)
    pygame.draw.rect(s, (72, 24, 35), frame, border_radius=12)
    pygame.draw.rect(s, (176, 131, 63), frame, 3, border_radius=12)
    pygame.draw.rect(s, (107, 67, 43), frame.inflate(-14, -14), 2, border_radius=8)
    pygame.draw.line(s, (246, 217, 148), (16, 5), (574, 5), 2)
    pygame.draw.line(s, (45, 25, 26), (14, 174), (576, 174), 3)
    # A coin-like medallion engraved with the Americas.
    pygame.draw.circle(s, (31, 28, 29), (79, 83), 54)
    pygame.draw.circle(s, (221, 178, 88), (77, 80), 54, 3)
    pygame.draw.circle(s, (109, 78, 46), (77, 80), 47, 1)
    for continent in (NORTH_AMERICA, SOUTH_AMERICA):
        pygame.draw.polygon(s, (219, 179, 91), continent)
        pygame.draw.lines(s, (249, 222, 155), False, continent[:5], 2)
    s.blit(title_font.render("THE AMERICAS", True, (250, 225, 168)), (146, 39))
    s.blit(subtitle_font.render("COMBAT ARMS REGION SIMULATOR", True, (202, 171, 128)), (148, 94))
    pygame.draw.line(s, (139, 98, 53), (146, 87), (558, 87), 1)
    branch(s, (150, 143), 1, 170)
    fleur(s, (358, 141), 23)
    branch(s, (563, 143), -1, 170)
    for x in (19, 574):
        for y in (18, 160):
            pygame.draw.circle(s, (244, 215, 143), (x, y), 3)
    return pygame.transform.smoothscale(s, SIZE)
