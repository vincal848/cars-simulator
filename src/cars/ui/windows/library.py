"""The campaign library: three save slots and the end-of-turn autosave."""

import pygame

from cars.persist.savegame import SaveLibrary
from cars.ui.frames import Window
from cars.ui.kit import style

SLOTS = range(SaveLibrary.SLOT_COUNT)


class _LibraryWindow(Window):
    icon = "chronicle"
    fit_content = True
    size = (620, 470)

    def __init__(self, game) -> None:
        super().__init__(game)
        self.library = SaveLibrary()
        self.confirm: str | None = None

    def on_open(self) -> None:
        super().on_open()
        self.confirm = None

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        y = rect.y
        height = ui.px(66)
        for i in SLOTS:
            action = f"slot{i}"
            row = pygame.Rect(rect.x, y, rect.width, height)
            ui.inset(
                row,
                style.SELECTED_ROW
                if self.confirm == action
                else style.PANEL_DARK
                if ui.hovered(row)
                else style.PANEL_LIGHT,
            )
            name = "Autosave" if i == SaveLibrary.AUTOSAVE else f"Slot {i + 1}"
            ui.text(name, (row.x + ui.px(14), row.y + ui.px(10)), style.HEADING, style.SLATE, bold=True)
            ui.text(
                self.library.describe(i),
                (row.x + ui.px(14), row.y + ui.px(36)),
                style.BODY,
                style.INK_MUTED,
                width=row.width - ui.px(28),
            )
            if i == SaveLibrary.AUTOSAVE:
                ui.hint(row, name, "Written automatically at the end of each turn.")
            self.clickable(row, action)
            y += height + ui.px(8)
        if self.notice:
            ui.text(self.notice, (rect.x, y + ui.px(4)), style.BODY, style.SLATE, width=rect.width)
            y += ui.px(30)
        return y - rect.y


class SaveWindow(_LibraryWindow):
    name = "save"
    title = "Save campaign"

    def act(self, action: str) -> None:
        slot = int(action[-1])
        path = self.library.path(slot)
        game = self.game
        if slot == SaveLibrary.AUTOSAVE:
            self.notice = "The autosave slot is written automatically at the end of each turn."
        elif game.view.animation or not game.campaign.human_turn:
            self.notice = "Save on your turn, after movement has finished."
        elif path.exists() and self.confirm != action:
            self.confirm = action
            self.notice = "Click this slot again to replace the save in it."
        else:
            game.save(path)
            self.notice = game.view.message
            self.confirm = None


class LoadWindow(_LibraryWindow):
    name = "load"
    title = "Load campaign"

    def act(self, action: str) -> None:
        slot = int(action[-1])
        if self.library.describe(slot) == "Empty slot":
            self.notice = "This slot is empty."
        elif self.confirm != action:
            self.confirm = action
            self.notice = "Click again to load this slot. Unsaved progress will be lost."
        elif not self.game.load(self.library.path(slot)):
            self.notice = self.game.view.message
