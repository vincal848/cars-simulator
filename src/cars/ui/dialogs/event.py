"""A scripted event awaiting the player's decision. It stays open until an option is chosen."""

import pygame

from cars.sim.events import EVENTS
from cars.ui.art.paintings import EVENTS as EVENT_PAINTINGS
from cars.ui.art.paintings import frame, painting
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import DIM

OPTION_HEIGHT = 48
PAINTING = pygame.Rect(268, 190, 664, 170)
# (text top, first option top), without and with an illustration.
PLAIN, ILLUSTRATED = (195, 330), (374, 452)


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

    def illustration(self) -> pygame.Surface | None:
        event = self.event
        return painting(EVENT_PAINTINGS, event.id, PAINTING.size) if event else None

    def layout(self) -> dict[str, pygame.Rect]:
        event = self.event
        count = len(event.options) if event else 0
        top = (ILLUSTRATED if self.illustration() else PLAIN)[1]
        return {f"option{i}": pygame.Rect(268, top + i * OPTION_HEIGHT, 664, 40) for i in range(count)}

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
        image = self.illustration()
        if image:
            frame(t.screen, image, PAINTING)
        text_top = (ILLUSTRATED if image else PLAIN)[0]
        t.paragraph(event.text, 268, text_top, 650, 3 if image else 10)
        for i, option in enumerate(event.options):
            t.button(self.buttons[f"option{i}"], option.label)
        t.text("Choose how your realm responds.", 268, 620, t.small, DIM)
