"""A scripted event awaiting the player's decision. It stays open until an option is chosen."""

import pygame

from cars.sim.events import EVENTS
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import DIM

OPTION_TOP = 330
OPTION_HEIGHT = 48


class EventDialog(Dialog):
    seal = "reports"
    closable = False

    @property
    def event(self):
        pending = self.game.state.events["pending"]
        return EVENTS[pending[0]] if pending else None

    @property
    def title(self) -> str:
        return self.event.title if self.event else ""

    def layout(self) -> dict[str, pygame.Rect]:
        event = self.event
        count = len(event.options) if event else 0
        return {f"option{i}": pygame.Rect(268, OPTION_TOP + i * OPTION_HEIGHT, 664, 40) for i in range(count)}

    def click(self, action: str) -> None:
        event = self.event
        ok, message = self.game.campaign.choose_event_option(event.id, int(action.removeprefix("option")))
        self.game.view.message = message
        if ok:
            self.game.dialogs.close()

    def draw(self) -> None:
        t = self.theme
        event = self.event
        if event is None:
            return
        t.paragraph(event.text, 268, 195, 650, 10)
        for i, option in enumerate(event.options):
            t.button(self.buttons[f"option{i}"], option.label)
        t.text("Choose how your realm responds.", 268, 620, t.small, DIM)
