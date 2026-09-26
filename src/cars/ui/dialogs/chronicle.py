"""The campaign chronicle: journal entries involving the player, newest first."""

import pygame

from cars.sim.journal import BATTLE_KINDS
from cars.ui.dialogs.base import PAGER, Dialog
from cars.ui.palette import DIM, GOLD
from cars.ui.text import wrap

VISIBLE_ROWS = 13
TEXT_WIDTH = 640


class ChronicleDialog(Dialog):
    title = "The Campaign Chronicle"
    seal = "reports"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.battles_only = True
        self.scroll = 0
        self.max_scroll = 0

    def on_open(self) -> None:
        super().on_open()
        self.scroll = 0

    def layout(self) -> dict[str, pygame.Rect]:
        return dict(PAGER)

    def entries(self) -> list[dict]:
        player = self.game.campaign.player
        entries = [r for r in reversed(self.game.state.reports) if player in r["participants"]]
        if self.battles_only:
            return [r for r in entries if r["kind"] in BATTLE_KINDS]
        return entries

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll - event.y * 2))
            return
        super().handle(event)

    def click(self, action: str) -> None:
        self.scroll = 0
        if action == "filter":
            self.battles_only = not self.battles_only
            self.page = 0
        elif action == "previous":
            self.page = max(0, self.page - 1)
        elif action == "next":
            self.page = min(max(0, len(self.entries()) - 1), self.page + 1)

    def draw(self) -> None:
        t = self.theme
        entries = self.entries()
        self.page = min(self.page, max(0, len(entries) - 1))
        if entries:
            self._draw_entry(entries[self.page], len(entries))
        else:
            t.text("No entries yet. Your campaign events will appear here.", 268, 230, t.body)
        t.button(self.buttons["previous"], "Newer")
        t.button(self.buttons["next"], "Older")
        t.button(self.buttons["filter"], "Battles only" if self.battles_only else "All campaign events")

    def _draw_entry(self, item: dict, count: int) -> None:
        t = self.theme
        province = self.game.state.provinces.get(item["location"])
        if province:
            place = province.name
        else:
            place = self.game.renderer.map.seas.get(item["location"], {}).get("name", item["location"])
        date = item.get("date", "Turn " + str(item["round"]))
        t.text(f"{date} / {item['kind'].title()} / {self.page + 1} of {count}", 268, 181, t.heading, GOLD)
        t.text(place, 268, 215, t.body, DIM, width=660)
        rows = [row for line in [item["summary"], *item["details"]] for row in wrap(line, t.body, TEXT_WIDTH)]
        self.max_scroll = max(0, len(rows) - VISIBLE_ROWS)
        self.scroll = min(self.scroll, self.max_scroll)
        for i, line in enumerate(rows[self.scroll : self.scroll + VISIBLE_ROWS]):
            t.text(line, 280, 252 + i * 23, t.body)
        if self.max_scroll:
            t.text("Scroll to read more losses and modifiers.", 280, 566, t.small, DIM)
