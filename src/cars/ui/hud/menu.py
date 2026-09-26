"""The top bar's Menu drop-down and CARSapedia button."""

from collections.abc import Callable
from typing import TYPE_CHECKING

import pygame

from cars.ui.palette import ROUTE_GOLD
from cars.ui.typography import FONT_CHOICES

if TYPE_CHECKING:
    from cars.ui.context import UiContext


class GameMenu:
    button = pygame.Rect(704, 16, 128, 32)
    pedia_button = pygame.Rect(334, 16, 140, 32)
    panel = pygame.Rect(582, 56, 250, 444)

    def __init__(self, context: "UiContext") -> None:
        self.context = context
        self.open = False
        # Item key -> (button, label). Keys double as the action taken when clicked.
        self.items: dict[str, tuple[pygame.Rect, Callable[[], str]]] = {
            "save": (pygame.Rect(590, 66, 236, 32), lambda: "Save campaign   /   F5"),
            "load": (pygame.Rect(590, 104, 236, 32), lambda: "Load campaign   /   F9"),
            "font": (pygame.Rect(590, 142, 236, 32), self._font_label),
            "market": (pygame.Rect(590, 180, 236, 32), lambda: "Merchant Exchange / M"),
            "display": (pygame.Rect(590, 220, 236, 32), self._display_label),
            "reports": (pygame.Rect(590, 260, 236, 32), lambda: "Campaign chronicle / J"),
            "settings": (pygame.Rect(590, 300, 236, 32), lambda: "Sound & preferences / F10"),
            "roster": (pygame.Rect(590, 340, 236, 32), lambda: "Military overview / U"),
            "pedia": (pygame.Rect(590, 380, 236, 32), lambda: "CARSapedia / F1"),
            "strategy": (pygame.Rect(590, 420, 236, 32), lambda: "Strategy graph / G"),
            "replay": (pygame.Rect(590, 460, 236, 32), lambda: "Replay studio / R"),
        }

    def _font_label(self) -> str:
        return FONT_CHOICES[self.context.theme.font_index][0] + "   /   Change font (F6)"

    def _display_label(self) -> str:
        return ("Windowed" if self.context.borderless else "Fullscreen windowed") + " / F11"

    def blocks(self, point) -> bool:
        return (
            self.button.collidepoint(point)
            or (self.open and self.panel.collidepoint(point))
            or self.pedia_button.collidepoint(point)
        )

    def item_at(self, point) -> str | None:
        return next((key for key, (rect, _) in self.items.items() if rect.collidepoint(point)), None)

    def draw(self) -> None:
        t = self.context.theme
        t.button(self.button, "Menu")
        t.button(self.pedia_button, "CARSapedia / F1")
        x, y = self.button.right - 17, self.button.centery
        if self.open:
            chevron = [(x - 4, y + 2), (x, y - 3), (x + 4, y + 2)]
        else:
            chevron = [(x - 4, y - 2), (x, y + 3), (x + 4, y - 2)]
        pygame.draw.lines(t.screen, ROUTE_GOLD, False, chevron, 1)
        if self.open:
            t.tips.begin()
            t.panel(self.panel)
            for rect, label in self.items.values():
                t.button(rect, label())
