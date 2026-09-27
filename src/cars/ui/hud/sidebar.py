"""The icon bar down the left edge, which opens the docked panels and the menu."""

from typing import TYPE_CHECKING

import pygame

from cars.ui.kit import style

if TYPE_CHECKING:
    from cars.ui.kit.ui import Ui

WIDTH = 56
BUTTON = 44
# (action, icon, title, help)
ITEMS = (
    ("nation", "nation", "Nation", "Your nation's history, traits, economy and objective. Shortcut: I."),
    ("military", "military", "Military", "Every army, fleet and balloon corps, sortable. Shortcut: U."),
    ("diplomacy", "diplomacy", "Diplomacy", "War, peace and the state of every rival. Shortcut: D."),
    ("market", "market", "Merchant Exchange", "Buy and sell lots of wood, food and iron. Shortcut: M."),
    ("chronicle", "chronicle", "Chronicle", "Battles and events of your campaign. Shortcut: J."),
    ("pedia", "pedia", "CARSapedia", "Every rule, unit, nation and building explained. Shortcut: F1."),
)
MENU = ("menu", "menu", "Menu", "Save, load, settings, replays and the strategic atlas. Shortcut: Esc.")


class Sidebar:
    def __init__(self, ui: "Ui") -> None:
        self.ui = ui
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.buttons: dict[str, pygame.Rect] = {}

    def layout(self, screen: pygame.Rect, top: int) -> None:
        ui = self.ui
        self.rect = pygame.Rect(0, top, ui.px(WIDTH), screen.bottom - top)
        size, left = ui.px(BUTTON), (self.rect.width - ui.px(BUTTON)) // 2
        self.buttons = {
            action: pygame.Rect(left, top + ui.px(10) + i * (size + ui.px(6)), size, size)
            for i, (action, *_rest) in enumerate(ITEMS)
        }
        self.buttons[MENU[0]] = pygame.Rect(left, self.rect.bottom - size - ui.px(10), size, size)

    def action_at(self, point) -> str | None:
        return next((action for action, rect in self.buttons.items() if rect.collidepoint(point)), None)

    def draw(self, open_panel: str | None) -> None:
        ui = self.ui
        pygame.draw.rect(ui.surface, style.SLATE_DARK, self.rect)
        pygame.draw.line(
            ui.surface,
            style.ACCENT,
            (self.rect.right - 1, self.rect.top),
            (self.rect.right - 1, self.rect.bottom),
            max(1, ui.px(1)),
        )
        for action, icon, title, help_text in (*ITEMS, MENU):
            rect = self.buttons[action]
            ui.icon_button(rect, icon, selected=action == open_panel)
            ui.hint(rect, title, help_text)
