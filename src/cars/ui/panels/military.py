"""The military panel: every army, fleet and air group in one sortable table."""

import pygame

from cars.sim.entities import AIR, FLEET
from cars.sim.regional import unit_name
from cars.ui.frames import DockedPanel
from cars.ui.kit import style
from cars.ui.kit.table import Column, Table

FILTERS = (("all", "All"), ("ready", "Ready"), ("cut off", "Cut off"), ("wounded", "Wounded"))
ARMS = {"land": "Army", FLEET: "Fleet", AIR: "Air group"}


class MilitaryPanel(DockedPanel):
    name = "military"
    title = "Military"
    icon = "military"
    width = 560

    def __init__(self, game) -> None:
        super().__init__(game)
        self.filter = "all"
        self.table = Table(
            [
                Column(
                    "Unit",
                    lambda u: unit_name(u),
                    hint="Click a row to select the unit and centre the map on it.",
                ),
                Column("Arm", lambda u: ARMS["land" if u.is_land else u.kind], width=80),
                Column("Location", lambda u: self.game.renderer.place_name(u.location), width=140),
                Column("Strength", lambda u: u.hp, width=84, align="right", color=_strength_color),
                Column("Orders", self._orders, width=86, align="right", sort=lambda u: u.remaining),
                Column(
                    "Supply",
                    lambda u: "Supplied" if u.supplied else "Cut off",
                    width=78,
                    color=lambda u: style.GOOD if u.supplied else style.BAD,
                ),
            ],
            sort=0,
        )

    @staticmethod
    def _orders(unit) -> str:
        if unit.kind == AIR:
            return "Sortie" if unit.remaining > 0 else "Spent"
        return f"{unit.remaining:g} / {unit.allowance:g}" if unit.remaining > 0 else "Spent"

    def units(self) -> list:
        player = self.game.campaign.player
        units = [u for u in self.state.units.values() if u.owner == player]
        if self.filter == "ready":
            units = [u for u in units if u.remaining > 0]
        elif self.filter == "cut off":
            units = [u for u in units if not u.supplied]
        elif self.filter == "wounded":
            units = [u for u in units if u.hp < 10]
        return units

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        body = self.body
        x, y = body.x, body.y
        width = ui.px(88)
        for i, (key, label) in enumerate(FILTERS):
            button = pygame.Rect(x + i * (width + ui.px(6)), y, width, ui.px(28))
            self.button(button, label, "filter:" + key, selected=self.filter == key)
        units = self.units()
        ui.text(f"{len(units)} units", (body.right, y + ui.px(5)), style.BODY, style.INK_MUTED, align="right")
        table_rect = pygame.Rect(body.x, y + ui.px(38), body.width, body.bottom - y - ui.px(38))
        selected = self.state.units.get(self.game.view.selected)
        self.table.draw(ui, table_rect, units, selected)
        return body.height  # The table scrolls itself.

    def handle(self, event: pygame.event.Event) -> bool:
        if self.contains(getattr(event, "pos", self.ui.mouse())):
            result = self.table.handle(event, self.ui)
            if result:
                kind, row = result
                if kind == "row":
                    self.game.focus_unit(row.id)
                return True
        return super().handle(event)

    def act(self, action: str) -> None:
        verb, _, value = action.partition(":")
        if verb == "filter":
            self.filter = value
            self.table.scroll = 0


def _strength_color(unit) -> tuple[int, int, int]:
    return style.GOOD if unit.hp > 6 else style.WARN if unit.hp > 3 else style.BAD
