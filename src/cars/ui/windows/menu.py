"""The game menu (Esc): files, settings, study tools and leaving the game."""

import pygame

from cars.ui.frames import Window
from cars.ui.kit import style

# (action, label, shortcut)
ITEMS = (
    ("resume", "Resume", "Esc"),
    ("save", "Save campaign", "F5"),
    ("load", "Load campaign", "F9"),
    ("settings", "Settings", "F10"),
    ("music", "Music collection", ""),
    ("keyboard", "Keyboard and mouse", ""),
    ("timeline", "Campaign calendar", "T"),
    ("strategy", "Strategic atlas", "G"),
    ("replay", "Replay studio", "R"),
    ("quit", "Quit to desktop", ""),
)


class MenuWindow(Window):
    name = "menu"
    title = "Menu"
    icon = "menu"
    fit_content = True
    size = (380, 560)

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        height, gap = ui.px(38), ui.px(6)
        for i, (action, label, shortcut) in enumerate(ITEMS):
            button = pygame.Rect(rect.x, rect.y + i * (height + gap), rect.width, height)
            self.button(button, label, action, kind="primary" if action == "resume" else "secondary")
            if shortcut:
                ui.text(
                    shortcut,
                    (button.right - ui.px(12), button.centery - ui.px(8)),
                    style.SMALL,
                    style.INK_FAINT if action != "resume" else style.ON_SLATE_MUTED,
                    align="right",
                )
        return len(ITEMS) * (height + gap)

    def act(self, action: str) -> None:
        if action == "resume":
            self.close()
        elif action == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        else:
            self.game.open_window(action)
