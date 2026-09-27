"""A scripted event awaiting the player's decision. It stays open until an option is chosen."""

import pygame

from cars.sim.events import EVENTS
from cars.ui.art.paintings import EVENTS as EVENT_PAINTINGS
from cars.ui.art.paintings import frame, painting
from cars.ui.frames import Window
from cars.ui.kit import style

PAINTING_SIZE = (664, 170)


class EventWindow(Window):
    name = "event"
    icon = "chronicle"
    closable = False
    size = (720, 560)

    @property
    def event(self):
        pending = self.state.events["pending"]
        return EVENTS[pending[0]] if pending else None

    def heading(self) -> str:
        return self.event.title if self.event else ""

    def illustration(self) -> pygame.Surface | None:
        event = self.event
        if event is None:
            return None
        return painting(
            EVENT_PAINTINGS, event.id, (self.ui.px(PAINTING_SIZE[0]), self.ui.px(PAINTING_SIZE[1]))
        )

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        event = self.event
        if event is None:
            return 0
        x, y, width = rect.x, rect.y, rect.width
        image = self.illustration()
        if image:
            area = image.get_rect(midtop=(rect.centerx, y))
            frame(ui.surface, image, area)
            y = area.bottom + ui.px(16)
        y += ui.paragraph(event.text, pygame.Rect(x, y, width, ui.px(200)), style.BODY) + ui.px(16)
        for i, option in enumerate(event.options):
            button = pygame.Rect(x, y, width, ui.px(40))
            self.button(button, option.label, f"option:{i}", kind="primary" if i == 0 else "secondary")
            y += ui.px(48)
        return y - rect.y

    def act(self, action: str) -> None:
        event = self.event
        index = int(action.removeprefix("option:"))
        ok, message = self.game.campaign.choose_event_option(event.id, index)
        self.game.view.message = message
        if ok:
            self.close()
