"""Military overview: every unit the player owns, with a filter and click-to-focus."""

import pygame

from cars.sim.entities import AIR
from cars.sim.regional import unit_name
from cars.ui.dialogs.base import PAGER, Dialog
from cars.ui.palette import DIM, GOLD

FILTERS = ("all", "ready", "cut off")
ROWS = 6


class RosterDialog(Dialog):
    title = "Military Overview"
    seal = "land"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.filter = "all"

    def layout(self) -> dict[str, pygame.Rect]:
        rows = {f"unit{i}": pygame.Rect(268, 235 + i * 51, 664, 46) for i in range(ROWS)}
        return rows | PAGER

    def units(self) -> list:
        state = self.game.state
        units = [u for u in state.units.values() if u.owner == self.game.campaign.player]
        if self.filter == "ready":
            units = [u for u in units if u.remaining > 0]
        if self.filter == "cut off":
            units = [u for u in units if not u.supplied]
        return sorted(units, key=lambda u: (u.kind, u.id))

    def _last_page(self, count: int) -> int:
        return max(0, (count - 1) // ROWS)

    def click(self, action: str) -> None:
        if action == "filter":
            self.filter = FILTERS[(FILTERS.index(self.filter) + 1) % len(FILTERS)]
            self.page = 0
        elif action == "previous":
            self.page = max(0, self.page - 1)
        elif action == "next":
            self.page = min(self._last_page(len(self.units())), self.page + 1)
        elif action.startswith("unit"):
            units = self.units()
            index = self.page * ROWS + int(action[-1])
            if index >= len(units):
                return
            if self.game.view.animation:
                self.notice = "Finish movement before focusing another unit."
            else:
                self.game.dialogs.close()
                self.game.focus_unit(units[index].id)

    def draw(self) -> None:
        t = self.theme
        state = self.game.state
        units = self.units()
        self.page = min(self.page, self._last_page(len(units)))
        t.text(
            f"{len(units)} units / Page {self.page + 1} / Click a row to focus its unit",
            268,
            184,
            t.body,
            DIM,
        )
        for i, unit in enumerate(units[self.page * ROWS : (self.page + 1) * ROWS]):
            box = self.buttons[f"unit{i}"]
            t.panel(box, box.collidepoint(t.mouse_pos()))
            province = state.provinces.get(unit.location)
            location = (
                province.name
                if province
                else self.game.renderer.map.seas.get(unit.location, {}).get("name", unit.location)
            )
            if not unit.supplied:
                status = "Cut off"
            else:
                status = "Ready" if unit.remaining > 0 else "Spent"
            if unit.kind == AIR:
                orders = "Sortie ready" if unit.remaining > 0 else "Sortie spent"
            else:
                orders = f"Move {unit.remaining:g}"
            t.text(unit_name(unit) + " / " + unit.id, box.x + 12, box.y + 5, t.body, GOLD, width=300)
            t.text(location, box.x + 12, box.y + 26, t.small, DIM, width=290)
            t.text(
                f"Strength {unit.hp:.1f}/10 / {orders} / {status}",
                box.x + 314,
                box.y + 15,
                t.small,
                width=338,
            )
        if not units:
            t.text("No units match this filter.", 280, 252, t.body)
        hint = self.notice or "N: next unit with orders / F: focus selection / Tab: cycle current layer"
        t.text(hint, 268, 565, t.small, DIM, width=664)
        t.button(self.buttons["previous"], "Previous")
        t.button(self.buttons["next"], "Next")
        t.button(self.buttons["filter"], "Show: " + self.filter.title())
