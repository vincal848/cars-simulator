"""The diplomacy panel: every rival nation in a table, and the state of war or peace with one.

Selecting a rival shows its history and traits and, when at war, the war itself:
the cities at stake with their victory points, occupation on both sides and who
is ahead. This is the only place victory points are drawn.
"""

import pygame

from cars.sim.diplomacy import RULES, leader, military_strength, quote_peace, quote_war, truce_ends
from cars.sim.nations import NATIONS
from cars.sim.objectives import controlled_cities
from cars.ui.frames import DockedPanel
from cars.ui.kit import style
from cars.ui.kit.grid import draw_grid, section
from cars.ui.kit.table import Column, Table

TABLE_ROWS = 7


class DiplomacyPanel(DockedPanel):
    name = "diplomacy"
    title = "Diplomacy"
    icon = "diplomacy"
    width = 600

    def __init__(self, game) -> None:
        super().__init__(game)
        self.selected: str | None = None
        self.table = Table(
            [
                Column("", lambda f: "", width=30, draw=self._swatch),
                Column("Nation", lambda f: self.state.factions[f].name),
                Column("Relation", self._relation, width=150, color=self._relation_color),
                Column(
                    "Strength", lambda f: round(military_strength(self.state, f)), width=82, align="right"
                ),
                Column("Cities", lambda f: len(controlled_cities(self.state, f)), width=62, align="right"),
                Column(
                    "Provinces",
                    lambda f: sum(p.controller == f for p in self.state.provinces.values()),
                    width=84,
                    align="right",
                ),
            ],
            row_height=32,
        )

    @property
    def player(self) -> str:
        return self.game.campaign.player

    def on_open(self) -> None:
        super().on_open()
        if self.selected is None:
            self.selected = next((f for f in self.state.factions if f != self.player), None)

    def _swatch(self, ui, cell: pygame.Rect, faction: str) -> None:
        ui.swatch(cell.center, self.state.factions[faction].color, 7)

    def _relation(self, faction: str) -> str:
        state = self.state
        if state.at_war(self.player, faction):
            return "At war"
        ends = truce_ends(state, self.player, faction)
        return f"Truce to round {ends}" if state.round < ends else "At peace"

    def _relation_color(self, faction: str):
        return style.BAD if self.state.at_war(self.player, faction) else style.GOOD

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        state = self.state
        rivals = [f for f in state.factions if f != self.player]
        x, y, width = rect.x, rect.y, rect.width
        lead = leader(state)
        if lead:
            note = (
                f"{state.factions[lead].name} holds a quarter of the continent's cities; the other "
                f"nations have formed a coalition against it."
            )
            y += ui.paragraph(note, pygame.Rect(x, y, width, ui.px(60)), style.SMALL, style.WARN) + ui.px(6)
        table_rect = pygame.Rect(x, y, width, ui.px(32) * (len(rivals) + 1))
        self.table.draw(ui, table_rect, rivals, self.selected)
        y = table_rect.bottom + ui.px(14)
        if self.selected in state.factions:
            y += self._detail(ui, x, y, width, self.selected)
        return y - rect.y + ui.px(8)

    def _detail(self, ui, x: int, y: int, width: int, faction: str) -> int:
        state = self.state
        rival = state.factions[faction]
        top = y
        ui.swatch((x + ui.px(9), y + ui.px(11)), rival.color, 9)
        ui.text(rival.name, (x + ui.px(26), y), style.TITLE - 2, style.SLATE, bold=True)
        y += ui.px(34)
        nation = NATIONS.get(faction)
        if nation:
            ui.text(
                f"{nation.ruler}  ·  {nation.government}", (x, y), style.SMALL, style.INK_MUTED, width=width
            )
            y += ui.px(22)
            y += ui.paragraph(nation.summary, pygame.Rect(x, y, width, ui.px(80)), style.BODY) + ui.px(4)
            traits = "   ·   ".join(f"{t.name}: {t.effect}" for t in nation.traits)
            y += ui.paragraph(traits, pygame.Rect(x, y, width, ui.px(60)), style.SMALL, style.SLATE) + ui.px(
                8
            )
        y += self._actions(ui, x, y, width, faction)
        if state.at_war(self.player, faction):
            y += ui.px(10)
            y += self._war(ui, x, y, width, faction)
        if self.notice:
            y += ui.px(8)
            y += ui.paragraph(self.notice, pygame.Rect(x, y, width, ui.px(60)), style.BODY, style.SLATE)
        return y - top

    def _actions(self, ui, x: int, y: int, width: int, faction: str) -> int:
        state = self.state
        at_war = state.at_war(self.player, faction)
        refusal = (
            quote_peace(state, self.player, faction) if at_war else quote_war(state, self.player, faction)
        )
        label = "Offer peace" if at_war else "Declare war"
        button = pygame.Rect(x, y, ui.px(170), ui.px(32))
        self.button(button, label, "treaty:" + faction, enabled=not refusal, kind="primary")
        effect = (
            f"Peace closes both borders and ends attacks for a {RULES.truce_rounds}-round truce."
            if at_war
            else "War reopens the border at once."
        )
        ui.hint(button, label, effect)
        if not refusal:
            return button.height + ui.px(6)
        ui.paragraph(
            refusal,
            pygame.Rect(button.right + ui.px(12), y + ui.px(2), width - button.width - ui.px(12), ui.px(40)),
            style.SMALL,
            style.INK_MUTED,
        )
        return button.height + ui.px(6)

    def _war(self, ui, x: int, y: int, width: int, faction: str) -> int:
        """The war between the player and ``faction``: every city either side claims or holds."""
        state = self.state
        top = y
        y += section(ui, "The war", x, y, width)
        sides = (self.player, faction)
        cities = [
            c
            for c in state.cities.values()
            if state.provinces[c.province].owner in sides or state.provinces[c.province].controller in sides
        ]
        mine = sum(state.provinces[c.province].controller == self.player for c in cities)
        theirs = sum(state.provinces[c.province].controller == faction for c in cities)
        occupied_by_me = sum(
            p.owner == faction and p.controller == self.player for p in state.provinces.values()
        )
        occupied_by_them = sum(
            p.owner == self.player and p.controller == faction for p in state.provinces.values()
        )
        balance = mine - theirs
        verdict = "You are ahead" if balance > 0 else "They are ahead" if balance < 0 else "Evenly matched"
        ui.text(
            f"{verdict}: {mine} to {theirs} victory points",
            (x, y),
            style.HEADING,
            style.GOOD if balance > 0 else style.BAD if balance < 0 else style.INK,
            bold=True,
        )
        y += ui.px(26)
        ui.text(
            f"You occupy {occupied_by_me} of their provinces; they occupy {occupied_by_them} of yours.",
            (x, y),
            style.BODY,
            style.INK_MUTED,
            width=width,
        )
        y += ui.px(26)

        def stars(area, city):
            holder = state.provinces[city.province].controller
            color = state.factions[holder].color
            ui.icon("star", (area.x + ui.px(14), area.centery), 18, tuple(color))

        rows = []
        for city in sorted(cities, key=lambda c: (state.provinces[c.province].owner != self.player, c.name)):
            province = state.provinces[city.province]
            holder = state.factions[province.controller].name
            claim = state.factions[province.owner].name
            rows.append(
                [
                    lambda area, city=city: stars(area, city),
                    city.name,
                    claim,
                    (
                        holder,
                        style.BAD
                        if province.controller == faction
                        else style.GOOD
                        if province.controller == self.player
                        else style.INK,
                    ),
                    "1",
                ]
            )
        columns = [
            ("VP", 34, "left"),
            ("City", None, "left"),
            ("Claimed by", 140, "left"),
            ("Held by", 140, "left"),
            ("Points", 58, "right"),
        ]
        y += draw_grid(ui, x, y, width, columns, rows)
        return y - top

    def handle(self, event: pygame.event.Event) -> bool:
        if self.contains(getattr(event, "pos", self.ui.mouse())) and event.type == pygame.MOUSEBUTTONDOWN:
            result = self.table.handle(event, self.ui)
            if result and result[0] == "row":
                self.selected = result[1]
                self.notice = ""
                return True
            if result:
                return True
        return super().handle(event)

    def act(self, action: str) -> None:
        verb, _, faction = action.partition(":")
        if verb == "treaty":
            campaign = self.game.campaign
            if self.state.at_war(self.player, faction):
                _, self.notice = campaign.propose_peace(faction)
            else:
                _, self.notice = campaign.declare_war(faction)
