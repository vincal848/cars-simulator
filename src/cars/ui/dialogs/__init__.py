"""Modal dialogs over the campaign. At most one is open; it captures all input."""

from typing import TYPE_CHECKING

import pygame

from cars.ui.dialogs.base import CLOSE_BUTTON, FRAME, Dialog
from cars.ui.dialogs.chronicle import ChronicleDialog
from cars.ui.dialogs.diplomacy import DiplomacyDialog
from cars.ui.dialogs.library import LoadDialog, SaveDialog
from cars.ui.dialogs.pedia import PediaDialog
from cars.ui.dialogs.replay_studio import ReplayStudioDialog
from cars.ui.dialogs.roster import RosterDialog
from cars.ui.dialogs.settings import MusicDialog, SettingsDialog
from cars.ui.dialogs.strategy import StrategyDialog
from cars.ui.dialogs.timeline import TimelineDialog

if TYPE_CHECKING:
    from cars.ui.screens.game import GameScreen

DIALOG_TYPES: dict[str, type[Dialog]] = {
    "save": SaveDialog,
    "load": LoadDialog,
    "music": MusicDialog,
    "settings": SettingsDialog,
    "reports": ChronicleDialog,
    "roster": RosterDialog,
    "diplomacy": DiplomacyDialog,
    "timeline": TimelineDialog,
    "pedia": PediaDialog,
    "strategy": StrategyDialog,
    "replay": ReplayStudioDialog,
}
SHADE = (6, 10, 16, 190)


class Dialogs:
    def __init__(self, game: "GameScreen") -> None:
        self.game = game
        self.mode: str | None = None
        self.dialogs = {mode: cls(game) for mode, cls in DIALOG_TYPES.items()}

    @property
    def active(self) -> Dialog | None:
        return self.dialogs[self.mode] if self.mode else None

    def open(self, mode: str) -> None:
        self.mode = mode
        self.game.renderer.menu.open = False
        self.active.on_open()
        if self.active.text_input:
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()

    def close(self) -> None:
        self.mode = None
        pygame.key.stop_text_input()

    def blocks(self, _point) -> bool:
        return self.mode is not None

    def event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
        else:
            self.active.handle(event)
        return True

    def draw(self) -> None:
        dialog = self.active
        if dialog is None:
            return
        t = self.game.context.theme
        t.tips.begin()
        t.dim_screen(SHADE)
        t.panel(FRAME)
        t.seal(dialog.seal, (284, 141), 39)
        t.text(dialog.title, 315, 127, t.serif)
        t.rule(268, 169, 664)
        t.button(CLOSE_BUTTON, "x")
        dialog.draw()
