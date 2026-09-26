"""Small province-window vignettes, one per terrain type."""

import math
import random

import pygame


def landscape(size: tuple[int, int], terrain: str) -> pygame.Surface:
    width, height = size
    canvas = pygame.Surface((width * 2, height * 2))
    W, H = canvas.get_size()
    rng = random.Random(terrain)
    for y in range(H):
        t = y / H
        pygame.draw.line(canvas, (int(161 - 51 * t), int(176 - 45 * t), int(172 - 52 * t)), (0, y), (W, y))
    pygame.draw.circle(canvas, (223, 211, 164), (int(W * 0.78), int(H * 0.24)), int(H * 0.13))
    for layer, color in [(0, (112, 134, 122)), (1, (82, 110, 89)), (2, (57, 85, 62))]:
        points = [(0, H)]
        for x in range(0, W + 10, 8):
            y = (
                H * (0.53 + layer * 0.13)
                + math.sin(x * 0.012 + layer) * H * 0.12
                + math.sin(x * 0.034) * H * 0.035
            )
            points.append((x, y))
        pygame.draw.polygon(canvas, color, [*points, (W, H)])
    if terrain == "mountains":
        peaks = [
            (W * 0.15, H * 0.17, W * 0.17),
            (W * 0.43, H * 0.08, W * 0.21),
            (W * 0.62, H * 0.28, W * 0.15),
        ]
        for x, y, wide in peaks:
            pygame.draw.polygon(canvas, (79, 91, 87), [(x - wide, H * 0.8), (x, y), (x + wide, H * 0.87)])
            pygame.draw.polygon(
                canvas, (159, 164, 149), [(x - wide, H * 0.8), (x, y), (x + wide * 0.14, H * 0.78)]
            )
            snow = [
                (x - wide * 0.28, y + H * 0.19),
                (x, y),
                (x + wide * 0.27, y + H * 0.21),
                (x, y + H * 0.14),
            ]
            pygame.draw.polygon(canvas, (225, 221, 196), snow)
    if terrain == "plains":
        for i in range(9):
            pygame.draw.line(canvas, (160, 158, 105), (W * 0.16 + i * 25, H), (W * 0.49 + i * 7, H * 0.72), 3)
    for _ in range(65 if terrain == "forest" else 13):
        x = rng.randrange(W)
        y = rng.randrange(int(H * 0.65), H)
        tree = rng.randrange(9, 28)
        pygame.draw.polygon(canvas, (38, 67, 48), [(x - 7, y), (x, y - tree), (x + 8, y)])
        pygame.draw.polygon(canvas, (93, 120, 75), [(x - 7, y), (x, y - tree), (x, y - 2)])
    return pygame.transform.smoothscale(canvas, size)
