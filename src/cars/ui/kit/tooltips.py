"""Delayed help cards. Widgets register hover areas while drawing; the card appears
after the pointer has rested on the same area for a moment."""

from typing import TYPE_CHECKING

import pygame

from cars.ui.kit import style
from cars.ui.text import wrap_breaking_words

if TYPE_CHECKING:
    from cars.ui.kit.ui import Ui

DELAY_MS = 350
WIDTH = 340


class Tooltips:
    def __init__(self) -> None:
        self.candidate: tuple[str, str, tuple] | None = None
        self.key: tuple | None = None
        self.since = 0
        self.last_rect: pygame.Rect | None = None

    def begin(self) -> None:
        """Forget hover areas registered so far, e.g. those hidden under a modal panel."""
        self.candidate = None

    def add(self, rect, title: str, body: str, point: tuple[int, int]) -> None:
        if pygame.Rect(rect).collidepoint(point):
            self.candidate = (str(title), str(body), tuple(pygame.Rect(rect)))

    def draw(self, ui: "Ui", force: bool = False, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else now
        self.last_rect = None
        if self.candidate is None:
            self.key = None
            return
        if self.candidate != self.key:
            self.key = self.candidate
            self.since = now
        if not force and now - self.since < DELAY_MS:
            return
        title, body, _ = self.candidate
        pad = ui.px(style.PAD)
        width = ui.px(WIDTH)
        body_font = ui.font(style.BODY)
        rows = wrap_breaking_words(body, body_font, width - pad * 2)
        line = round(body_font.get_height() * 1.3)
        title_height = ui.font(style.HEADING, bold=True).get_height()
        height = pad * 2 + title_height + ui.px(8) + len(rows) * line
        mouse_x, mouse_y = ui.mouse()
        screen = ui.screen
        offset = ui.px(18)
        x = mouse_x + offset if mouse_x + offset + width < screen.width else mouse_x - width - offset
        y = mouse_y + offset if mouse_y + offset + height < screen.height else mouse_y - height - offset
        rect = pygame.Rect(x, y, width, min(height, screen.height - pad * 2))
        rect.clamp_ip(screen.inflate(-pad, -pad))
        self.last_rect = rect
        ui.shadow(rect, 4)
        pygame.draw.rect(ui.surface, style.PANEL_LIGHT, rect)
        ui.frame(rect)
        ui.text(
            title, (rect.x + pad, rect.y + pad), style.HEADING, style.SLATE, width=width - pad * 2, bold=True
        )
        y = rect.y + pad + title_height + ui.px(8)
        for row in rows:
            if y + line > rect.bottom - pad // 2:
                break
            ui.text(row, (rect.x + pad, y), style.BODY, style.INK)
            y += line
