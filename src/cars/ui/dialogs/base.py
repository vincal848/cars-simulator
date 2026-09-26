"""Modal dialogs share one framed window, a close button and simple button routing."""

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from cars.ui.screens.game import GameScreen
    from cars.ui.theme import Theme

FRAME = pygame.Rect(240, 104, 720, 560)
CLOSE_BUTTON = pygame.Rect(922, 120, 30, 28)
PAGER = dict(
    previous=pygame.Rect(270, 600, 130, 32),
    next=pygame.Rect(794, 600, 130, 32),
    filter=pygame.Rect(426, 600, 338, 32),
)


class Dialog:
    title = ""
    seal = "reports"
    text_input = False

    def __init__(self, game: "GameScreen") -> None:
        self.game = game
        self.buttons: dict[str, pygame.Rect] = {}
        self.page = 0
        self.notice = ""

    @property
    def theme(self) -> "Theme":
        return self.game.context.theme

    def on_open(self) -> None:
        self.page = 0
        self.notice = ""
        # The close button comes first so it wins over anything beneath it.
        self.buttons = {"close": CLOSE_BUTTON, **self.layout()}

    def layout(self) -> dict[str, pygame.Rect]:
        return {}

    def action_at(self, point) -> str | None:
        return next((name for name, rect in self.buttons.items() if rect.collidepoint(point)), None)

    def handle(self, event: pygame.event.Event) -> None:
        """Route a left click to :meth:`click`; dialogs capture every other event."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        action = self.action_at(event.pos)
        if action == "close":
            self.game.dialogs.close()
        elif action:
            self.click(action)

    def click(self, action: str) -> None:
        pass

    def draw(self) -> None:
        pass
