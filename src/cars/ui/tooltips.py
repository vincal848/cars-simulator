"""Delayed help cards. Widgets register hover areas while drawing; the card appears
after the pointer has rested on the same area for a moment."""

from typing import TYPE_CHECKING

import pygame

from cars.ui.text import wrap_breaking_words

if TYPE_CHECKING:
    from cars.ui.theme import Theme

DELAY_MS = 350
WIDTH = 338
TEXT_WIDTH = 310
LINE_HEIGHT = 20
TITLE_COLOR = (244, 209, 133)


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

    def draw(self, theme: "Theme", force: bool = False, now: int | None = None) -> None:
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
        rows = wrap_breaking_words(body, theme.body, TEXT_WIDTH)
        height = min(730, 51 + len(rows) * LINE_HEIGHT)
        mouse_x, mouse_y = theme.mouse_pos()
        screen = theme.screen
        x = mouse_x + 18 if mouse_x + 356 < screen.get_width() else mouse_x - 356
        y = mouse_y + 23 if mouse_y + height + 23 < screen.get_height() else mouse_y - height - 15
        rect = pygame.Rect(x, y, WIDTH, height)
        rect.clamp_ip(screen.get_rect().inflate(-16, -16))
        self.last_rect = rect
        theme.panel(rect, True)
        theme.text(title, rect.x + 13, rect.y + 10, theme.heading, TITLE_COLOR, width=TEXT_WIDTH)
        for i, row in enumerate(rows[: (height - 46) // LINE_HEIGHT]):
            theme.text(row, rect.x + 13, rect.y + 37 + i * LINE_HEIGHT, theme.body)
