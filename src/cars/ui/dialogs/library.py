"""The campaign library: three save slots and the end-of-turn autosave."""

import pygame

from cars.persist.savegame import SaveLibrary
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import DIM, GOLD

SLOTS = range(SaveLibrary.SLOT_COUNT)


class _SlotDialog(Dialog):
    seal = "reports"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.library = SaveLibrary()
        self.confirm: str | None = None

    def on_open(self) -> None:
        super().on_open()
        self.confirm = None

    def layout(self) -> dict[str, pygame.Rect]:
        return {f"slot{i}": pygame.Rect(268, 224 + i * 86, 664, 70) for i in SLOTS}

    def draw(self) -> None:
        t = self.theme
        t.text("Three manual slots and a separate end-turn autosave.", 268, 180, t.body, DIM)
        for i in SLOTS:
            box = self.buttons[f"slot{i}"]
            t.panel(box, self.confirm == f"slot{i}")
            name = "Autosave" if i == SaveLibrary.AUTOSAVE else f"Campaign slot {i + 1}"
            t.text(name, box.x + 15, box.y + 10, t.heading, GOLD)
            t.text(self.library.describe(i), box.x + 15, box.y + 39, t.body, DIM, width=630)
        t.text(
            self.notice or "Click a slot to select it. Esc returns to the game.", 268, 600, t.body, width=664
        )


class SaveDialog(_SlotDialog):
    title = "Save Campaign"

    def click(self, action: str) -> None:
        slot = int(action[-1])
        path = self.library.path(slot)
        game = self.game
        if slot == SaveLibrary.AUTOSAVE:
            self.notice = "Autosave is managed automatically."
        elif game.view.animation or not game.campaign.human_turn:
            self.notice = "Save on your turn after movement finishes."
        elif path.exists() and self.confirm != action:
            self.confirm = action
            self.notice = "Click this slot again to replace its save."
        else:
            game.save(path)
            self.notice = game.view.message
            self.confirm = None


class LoadDialog(_SlotDialog):
    title = "Campaign Library"

    def click(self, action: str) -> None:
        slot = int(action[-1])
        if self.library.describe(slot) == "Empty slot":
            self.notice = "This slot is empty."
        elif self.confirm != action:
            self.confirm = action
            self.notice = "Click again to load this slot. Unsaved progress will be replaced."
        elif not self.game.load(self.library.path(slot)):
            self.notice = self.game.view.message
