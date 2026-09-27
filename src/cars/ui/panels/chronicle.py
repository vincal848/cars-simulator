"""The chronicle: every journal entry involving the player, newest first, with filters."""

import pygame

from cars.sim.journal import BATTLE_KINDS
from cars.ui.battle import draw_losses, draw_modifiers
from cars.ui.frames import DockedPanel
from cars.ui.kit import style

FILTERS = (("battles", "Battles"), ("all", "Everything"))


class ChroniclePanel(DockedPanel):
    name = "chronicle"
    title = "Chronicle"
    icon = "chronicle"
    width = 520

    def __init__(self, game) -> None:
        super().__init__(game)
        self.filter = "battles"

    def entries(self) -> list[dict]:
        player = self.game.campaign.player
        entries = [r for r in reversed(self.state.reports) if player in r["participants"]]
        if self.filter == "battles":
            entries = [r for r in entries if r["kind"] in BATTLE_KINDS]
        return entries

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        x, y, width = rect.x, rect.y, rect.width
        button_width = ui.px(110)
        for i, (key, label) in enumerate(FILTERS):
            button = pygame.Rect(x + i * (button_width + ui.px(6)), y, button_width, ui.px(28))
            self.button(button, label, "filter:" + key, selected=self.filter == key)
        y += ui.px(40)
        entries = self.entries()
        if not entries:
            ui.text("Nothing recorded yet.", (x, y), style.BODY, style.INK_FAINT)
            return ui.px(80)
        for entry in entries:
            y += self._entry(ui, x, y, width, entry) + ui.px(10)
        return y - rect.y

    def _entry(self, ui, x: int, y: int, width: int, entry: dict) -> int:
        top = y
        battle = entry["kind"] in BATTLE_KINDS
        place = self.game.renderer.place_name(entry["location"]) if entry["location"] else ""
        ui.text(entry.get("date", f"Round {entry['round']}"), (x, y), style.SMALL, style.INK_MUTED, bold=True)
        ui.text(
            entry["kind"].title() + (f" · {place}" if place else ""),
            (x + width, y),
            style.SMALL,
            style.BAD if battle else style.SLATE,
            align="right",
            width=width // 2,
        )
        y += ui.px(18)
        y += ui.paragraph(entry["summary"], pygame.Rect(x, y, width, ui.px(200)), style.BODY)
        if "losses" in entry:
            y += ui.px(6)
            y += draw_modifiers(ui, x, y, width, entry["factors"])
            y += ui.px(8)
            y += draw_losses(ui, x, y, width, self.state, entry["losses"])
        else:
            for line in entry["details"]:
                y += ui.paragraph(
                    line,
                    pygame.Rect(x + ui.px(12), y, width - ui.px(12), ui.px(200)),
                    style.SMALL,
                    style.INK_MUTED,
                )
        ui.rule(x, x + width, y + ui.px(4))
        return y - top + ui.px(4)

    def act(self, action: str) -> None:
        verb, _, value = action.partition(":")
        if verb == "filter":
            self.filter = value
            self.scroll = 0
