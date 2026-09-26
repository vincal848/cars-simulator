"""Shared interface colours and fixed canvas geometry."""

import pygame

# The UI is laid out on a fixed logical canvas and scaled to the window.
CANVAS_SIZE = (1200, 780)
MAP_AREA = pygame.Rect(0, 0, 1200, 742)

# Parchment-and-brass panels.
INK = (15, 25, 32)
PAPER = (250, 230, 191)
GOLD = (219, 179, 91)
DIM = (198, 172, 151)
GREEN = (145, 194, 140)
WELL = (23, 19, 23)

# Map overlays.
OCEAN = (15, 30, 43)
MAP_TEXT = (229, 233, 221)
MAP_MUTED = (149, 171, 181)
ROUTE_GOLD = (245, 207, 115)
HOSTILE = (245, 142, 115)
SUPPLY_GREEN = (114, 219, 161)
TARGET_RED = (247, 139, 104)
