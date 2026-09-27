"""A reference card of every key and mouse control."""

import pygame

from cars.ui.frames import Window
from cars.ui.kit.grid import draw_grid, section

CONTROLS = (
    (
        "Map",
        (
            ("Left click", "Select an army, order a move or attack, or open a province"),
            ("Right click", "Open a province"),
            ("Left or middle drag", "Pan the map"),
            ("Mouse wheel", "Zoom"),
            ("Home", "World view"),
            ("1 2 3 4", "Political, terrain, supply and diplomatic map"),
        ),
    ),
    (
        "Units",
        (
            ("N", "Next unit with orders"),
            ("Tab", "Next unit in the same place"),
            ("F", "Centre on the selected unit"),
            ("Esc", "Close the panel, then clear the selection, then open the menu"),
            ("Space", "End Turn"),
        ),
    ),
    (
        "Panels and windows",
        (
            ("I / U / D / M / J", "Nation, military, diplomacy, market and chronicle panels"),
            ("F1", "CARSapedia"),
            ("T / G / R", "Calendar, strategic atlas and replay studio"),
            ("F5 / F9", "Save and load"),
            ("F6 / F10 / F11", "Typeface, settings and fullscreen"),
            ("H", "Hide or show the tutorial"),
            ("F3", "Debug view of the movement graph"),
        ),
    ),
)


class KeyboardWindow(Window):
    name = "keyboard"
    title = "Keyboard and mouse"
    icon = "settings"
    fit_content = True
    size = (700, 640)

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        y = rect.y
        for title, rows in CONTROLS:
            y += section(ui, title, rect.x, y, rect.width)
            y += draw_grid(
                ui, rect.x, y, rect.width, [("Input", 170, "left"), ("Action", None, "left")], rows
            ) + ui.px(14)
        return y - rect.y
