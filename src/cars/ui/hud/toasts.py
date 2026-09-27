"""Short notifications under the top bar that fade after a few seconds."""

from typing import TYPE_CHECKING

import pygame

from cars.ui.kit import style

if TYPE_CHECKING:
    from cars.ui.kit.ui import Ui

LIFETIME = 6.0
FADE = 1.0
LIMIT = 3
WIDTH = 520


class Toasts:
    def __init__(self, ui: "Ui") -> None:
        self.ui = ui
        self.items: list[tuple[str, float]] = []
        self.now = 0.0
        self.last = ""

    def push(self, text: str) -> None:
        if not text or text == self.last:
            return
        self.last = text
        self.items = [*self.items, (text, self.now)][-LIMIT:]

    def update(self, dt: float) -> None:
        self.now += dt
        self.items = [(text, born) for text, born in self.items if self.now - born < LIFETIME]

    def draw(self, top: int, left: int, right: int) -> None:
        """Draw the notifications centred between ``left`` and ``right``, below ``top``."""
        ui = self.ui
        y = top + ui.px(10)
        limit = min(ui.px(WIDTH), right - left - ui.px(24))
        for text, born in reversed(self.items):
            age = self.now - born
            alpha = 255 if age < LIFETIME - FADE else round(255 * (LIFETIME - age) / FADE)
            font = ui.font(style.BODY)
            label = font.render(ui.fit(text, font, limit - ui.px(24)), True, style.ON_SLATE)
            box = pygame.Rect(0, y, label.get_width() + ui.px(24), label.get_height() + ui.px(10))
            box.centerx = (left + right) // 2
            card = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(card, (*style.SLATE_DARK, 225), card.get_rect(), border_radius=ui.px(4))
            pygame.draw.rect(
                card, (*style.BRASS, 255), card.get_rect(), max(1, ui.px(1)), border_radius=ui.px(4)
            )
            card.blit(label, label.get_rect(center=card.get_rect().center))
            card.set_alpha(alpha)
            ui.surface.blit(card, box)
            y = box.bottom + ui.px(6)
