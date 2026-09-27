"""The nation panel: history, national traits, the economy in figures and the objective."""

import pygame

from cars.sim.economy import forecast, storage
from cars.sim.entities import BALLOON, FLEET, RESOURCES
from cars.sim.market import treasury_income
from cars.sim.nations import NATIONS
from cars.sim.objectives import ACTIVE, campaign_stage, controlled_cities
from cars.sim.upkeep import upkeep
from cars.ui.frames import DockedPanel
from cars.ui.kit import style
from cars.ui.kit.grid import draw_grid, facts, section

STAGES = ("Foothold", "Expansion", "Consolidation", "Dominion")


class NationPanel(DockedPanel):
    name = "nation"
    icon = "nation"
    width = 470

    @property
    def faction(self) -> str:
        return self.game.campaign.player or self.state.active

    def heading(self) -> str:
        return self.state.factions[self.faction].name

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        state = self.state
        faction = state.factions[self.faction]
        nation = NATIONS.get(self.faction)
        x, y, width = rect.x, rect.y, rect.width
        ui.swatch((x + ui.px(10), y + ui.px(12)), faction.color, 10)
        if nation:
            ui.text(nation.government, (x + ui.px(28), y), style.BODY, style.INK, width=width - ui.px(28))
            ui.text(f"“{nation.motto}”", (x + ui.px(28), y + ui.px(20)), style.BODY, style.SLATE, italic=True)
            y += ui.px(50)
            y += facts(
                ui,
                x,
                y,
                width,
                [
                    ("Ruler", nation.ruler),
                    ("Capital", nation.capital),
                    ("Founded", str(nation.founded)),
                    ("Uniform", faction.style.title()),
                ],
            )
            y += ui.px(6)
            y += section(ui, "History", x, y, width)
            for paragraph in nation.history:
                y += ui.paragraph(paragraph, pygame.Rect(x, y, width, ui.px(400)), style.BODY) + ui.px(8)
            y += ui.px(6)
            y += section(ui, "National traits", x, y, width)
            rows = [[(trait.name, style.SLATE), trait.effect] for trait in nation.traits]
            y += draw_grid(ui, x, y, width, [("Trait", 150, "left"), ("Effect", None, "left")], rows)
        y += ui.px(14)
        y += section(ui, "Economy", x, y, width)
        y += self._economy(ui, x, y, width)
        y += ui.px(14)
        y += section(ui, "Realm", x, y, width)
        y += self._realm(ui, x, y, width)
        if state.objectives.get("player"):
            y += ui.px(14)
            y += section(ui, "Objective", x, y, width)
            y += self._objective(ui, x, y, width)
        return y - rect.y + ui.px(8)

    def _economy(self, ui, x: int, y: int, width: int) -> int:
        state = self.state
        owner = self.faction
        stock = state.factions[owner].resources
        gains = forecast(state, owner)
        costs = upkeep(state, owner)
        limit = storage(state, owner)
        rows = []
        for resource in RESOURCES:
            net = gains[resource] - costs[resource]
            rows.append(
                [
                    resource.title(),
                    f"{stock[resource]:,.0f}",
                    f"{limit}",
                    (f"+{gains[resource]:.1f}", style.GOOD),
                    (f"−{costs[resource]:.1f}", style.BAD if costs[resource] else style.INK_MUTED),
                    (f"{net:+.1f}", style.GOOD if net >= 0 else style.BAD),
                ]
            )
        gold = state.factions[owner].gold
        income = treasury_income(state, owner)
        rows.append(
            [
                "Gold",
                f"{gold:,.0f}",
                "—",
                (f"+{income}", style.GOOD),
                ("—", style.INK_MUTED),
                (f"+{income}", style.GOOD),
            ]
        )
        columns = [
            ("", None, "left"),
            ("Stock", 64, "right"),
            ("Capacity", 76, "right"),
            ("Income", 70, "right"),
            ("Upkeep", 70, "right"),
            ("Net", 64, "right"),
        ]
        return draw_grid(ui, x, y, width, columns, rows)

    def _realm(self, ui, x: int, y: int, width: int) -> int:
        state = self.state
        owner = self.faction
        held = [p for p in state.provinces.values() if p.controller == owner]
        occupied = sum(p.owner != owner for p in held)
        lost = sum(p.owner == owner and p.controller != owner for p in state.provinces.values())
        units = [u for u in state.units.values() if u.owner == owner]
        pairs = [
            ("Provinces", f"{len(held)}" + (f", {occupied} occupied" if occupied else "")),
            ("Cities", str(len(controlled_cities(state, owner)))),
            ("Lost to enemies", (str(lost), style.BAD) if lost else "None"),
            ("Armies", str(sum(u.is_land for u in units))),
            ("Fleets", str(sum(u.kind == FLEET for u in units))),
            ("Balloon corps", str(sum(u.kind == BALLOON for u in units))),
        ]
        return facts(ui, x, y, width, pairs, columns=3)

    def _objective(self, ui, x: int, y: int, width: int) -> int:
        state = self.state
        goal = state.objectives
        stage = campaign_stage(state)
        rules = goal["rules"]
        top = y
        status = stage.name if goal["status"] == ACTIVE else goal["status"].title()
        ui.text(status, (x, y), style.HEADING, style.SLATE, bold=True)
        y += ui.px(26)
        y += ui.paragraph(stage.goal, pygame.Rect(x, y, width, ui.px(60)), style.BODY) + ui.px(6)
        step = width // len(STAGES)
        for i, name in enumerate(STAGES):
            reached = i <= stage.index
            bar = pygame.Rect(x + i * step, y, step - ui.px(6), ui.px(6))
            pygame.draw.rect(
                ui.surface, style.HIGHLIGHT if reached else style.PARCHMENT_DARK, bar, border_radius=ui.px(3)
            )
            ui.text(
                name, (bar.x, bar.bottom + ui.px(4)), style.SMALL, style.INK if reached else style.INK_FAINT
            )
        y += ui.px(34)
        cities = len(controlled_cities(state, goal["player"]))
        ui.text(
            f"Cities held {cities} of {rules['cities']}   ·   Rounds held {goal['held']} of {rules['turns']}",
            (x, y),
            style.BODY,
            style.INK_MUTED,
        )
        return y - top + ui.px(24)
