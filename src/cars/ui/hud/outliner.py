"""The outliner down the right edge: the objective, then every army, fleet, balloon corps and city.

Sections collapse by clicking their headers. Clicking a unit selects and centres it;
clicking a city opens its province. A gold dot marks units that still have orders.
"""

from typing import TYPE_CHECKING

import pygame

from cars.sim.entities import BALLOON, FLEET
from cars.sim.objectives import ACTIVE, campaign_stage, controlled_cities
from cars.sim.regional import unit_name
from cars.ui.kit import style

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.kit.ui import Ui

WIDTH = 286
HEADER = 30
ROW = 26
SECTIONS = (("armies", "Armies"), ("fleets", "Fleets"), ("balloons", "Balloon corps"), ("cities", "Cities"))


class Outliner:
    def __init__(self, ui: "Ui") -> None:
        self.ui = ui
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.open = {"goal": True, "armies": True, "fleets": False, "balloons": False, "cities": False}
        self.scroll = 0
        self.areas: list[tuple[pygame.Rect, str]] = []
        self.limit = pygame.Rect(0, 0, 0, 0)

    def layout(self, screen: pygame.Rect, top: int, bottom: int) -> None:
        ui = self.ui
        self.limit = pygame.Rect(
            screen.right - ui.px(WIDTH) - ui.px(8), top + ui.px(8), ui.px(WIDTH), bottom - top - ui.px(16)
        )

    def contains(self, point) -> bool:
        return self.rect.collidepoint(point)

    def action_at(self, point) -> str | None:
        if not self.rect.collidepoint(point):
            return None
        return next((action for rect, action in reversed(self.areas) if rect.collidepoint(point)), None)

    def rows(self, state: "GameState", player: str, selected: str | None) -> list[tuple]:
        """(kind, content) rows in drawing order."""
        own = sorted((u for u in state.units.values() if u.owner == player), key=lambda u: (u.kind, u.id))
        groups = {
            "armies": [u for u in own if u.is_land],
            "fleets": [u for u in own if u.kind == FLEET],
            "balloons": [u for u in own if u.kind == BALLOON],
            "cities": controlled_cities(state, player),
        }
        rows: list[tuple] = [("header", "goal", "Objective", None)]
        if self.open["goal"] and state.objectives.get("player"):
            rows.append(("goal", None))
        for key, title in SECTIONS:
            rows.append(("header", key, title, len(groups[key])))
            if self.open[key]:
                kind = "city" if key == "cities" else "unit"
                rows += [(kind, item) for item in groups[key]]
        return rows

    def draw(self, state: "GameState", player: str, selected: str | None) -> None:
        ui = self.ui
        self.areas = []
        rows = self.rows(state, player, selected)
        heights = [ui.px(HEADER if row[0] == "header" else 76 if row[0] == "goal" else ROW) for row in rows]
        height = min(self.limit.height, sum(heights) + ui.px(8))
        self.rect = pygame.Rect(self.limit.x, self.limit.y, self.limit.width, height)
        ui.shadow(self.rect, 4)
        pygame.draw.rect(ui.surface, style.PANEL, self.rect)
        ui.frame(self.rect)
        inner = self.rect.inflate(-ui.px(8), -ui.px(8))
        self.scroll = max(0, min(self.scroll, sum(heights) - inner.height))
        y = inner.y - self.scroll
        with ui.clip(inner):
            for row, row_height in zip(rows, heights, strict=True):
                line = pygame.Rect(inner.x, y, inner.width, row_height)
                if line.bottom > inner.top and line.top < inner.bottom:
                    self._draw_row(state, row, line, selected)
                y += row_height

    def _draw_row(self, state: "GameState", row: tuple, line: pygame.Rect, selected: str | None) -> None:
        ui = self.ui
        kind = row[0]
        pad = ui.px(8)
        if kind == "header":
            _, key, title, count = row
            pygame.draw.rect(ui.surface, style.SLATE, line.inflate(0, -ui.px(4)), border_radius=ui.px(3))
            ui.disclosure((line.x + pad + ui.px(4), line.centery), self.open[key])
            ui.text(
                title,
                (line.x + pad * 2 + ui.px(8), line.centery - ui.px(9)),
                style.BODY,
                style.ON_SLATE,
                bold=True,
            )
            if count is not None:
                ui.text(
                    str(count),
                    (line.right - pad, line.centery - ui.px(9)),
                    style.BODY,
                    style.ON_SLATE_MUTED,
                    align="right",
                )
            self.areas.append((line, "toggle:" + key))
        elif kind == "goal":
            self._draw_goal(state, line)
        elif kind == "unit":
            unit = row[1]
            if unit.id == selected:
                pygame.draw.rect(ui.surface, style.SELECTED_ROW, line)
            elif ui.hovered(line):
                pygame.draw.rect(ui.surface, style.HOVER_ROW, line)
            ready = unit.remaining > 0
            dot = (line.x + pad, line.centery)
            pygame.draw.circle(ui.surface, style.HIGHLIGHT if ready else style.RULE, dot, ui.px(4))
            name = unit_name(unit)
            place = (
                state.provinces[unit.location].name
                if unit.location in state.provinces
                else unit.location.replace("_", " ").title()
            )
            ui.text(
                name, (line.x + pad * 2, line.centery - ui.px(9)), style.BODY, style.INK, width=ui.px(120)
            )
            ui.text(
                place,
                (line.right - pad, line.centery - ui.px(8)),
                style.SMALL,
                style.INK_MUTED,
                width=ui.px(110),
                align="right",
            )
            strength = pygame.Rect(line.x + pad * 2, line.bottom - ui.px(4), ui.px(120), ui.px(2))
            ui.progress(
                strength,
                unit.hp / 10,
                style.GOOD if unit.hp > 6 else style.WARN if unit.hp > 3 else style.BAD,
            )
            if not unit.supplied:
                ui.text(
                    "cut off",
                    (line.right - pad - ui.px(112), line.centery - ui.px(8)),
                    style.SMALL,
                    style.BAD,
                )
            self.areas.append((line, "unit:" + unit.id))
        elif kind == "city":
            city = row[1]
            if ui.hovered(line):
                pygame.draw.rect(ui.surface, style.HOVER_ROW, line)
            ui.icon("province", (line.x + pad + ui.px(4), line.centery), 16, style.INK_MUTED)
            ui.text(
                city.name,
                (line.x + pad * 2 + ui.px(8), line.centery - ui.px(9)),
                style.BODY,
                style.INK,
                width=ui.px(150),
            )
            ui.text(
                state.provinces[city.province].name,
                (line.right - pad, line.centery - ui.px(8)),
                style.SMALL,
                style.INK_MUTED,
                width=ui.px(100),
                align="right",
            )
            self.areas.append((line, "city:" + city.id))

    def _draw_goal(self, state: "GameState", line: pygame.Rect) -> None:
        ui = self.ui
        goal = state.objectives
        stage = campaign_stage(state)
        rules = goal["rules"]
        cities = len(controlled_cities(state, goal["player"]))
        pad = ui.px(8)
        status = f"{stage.index + 1}. {stage.name}" if goal["status"] == ACTIVE else goal["status"].title()
        ui.text(
            status,
            (line.x + pad, line.y + ui.px(4)),
            style.BODY,
            style.SLATE,
            bold=True,
            width=line.width - pad * 2,
        )
        ui.text(
            f"Cities {cities} of {rules['cities']}   ·   Rounds held {goal['held']} of {rules['turns']}",
            (line.x + pad, line.y + ui.px(26)),
            style.SMALL,
            style.INK_MUTED,
            width=line.width - pad * 2,
        )
        bar = pygame.Rect(line.x + pad, line.y + ui.px(48), line.width - pad * 2, ui.px(7))
        ui.progress(bar, goal["held"] / rules["turns"])
        ui.hint(
            line,
            "Dominion objective",
            f"Hold at least {rules['cities']} cities for {rules['turns']} consecutive full rounds. "
            f"{stage.goal} Dropping below the city target resets the count.",
        )

    def handle_action(self, action: str, game) -> None:
        kind, _, value = action.partition(":")
        if kind == "toggle":
            self.open[value] = not self.open[value]
        elif kind == "unit":
            game.focus_unit(value)
        elif kind == "city":
            city = game.state.cities[value]
            game.renderer.map.center_on(city.province)
            game.inspect(city.province)

    def scroll_by(self, steps: int) -> None:
        self.scroll = max(0, self.scroll - steps * self.ui.px(ROW) * 2)
