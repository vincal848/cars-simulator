"""The selected unit's card along the bottom of the map, with its air missions."""

from typing import TYPE_CHECKING

import pygame

from cars.sim.air import MISSIONS
from cars.sim.entities import AIR, FULL_STRENGTH
from cars.sim.recovery import recovery_rate
from cars.sim.regional import unit_name
from cars.sim.upkeep import unit_upkeep
from cars.ui.kit import style

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.kit.ui import Ui

SIZE = (470, 108)
MISSION_HELP = {
    "strike": "Attack an enemy army or fleet in range. Uses the sortie; expect return fire.",
    "support": "Give +25% attack to your land attacks into one province until your next turn.",
    "rebase": "Fly to another airbase you control within range.",
}


class UnitCard:
    def __init__(self, ui: "Ui") -> None:
        self.ui = ui
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.areas: list[tuple[pygame.Rect, str]] = []

    def layout(self, screen: pygame.Rect, left: int) -> None:
        ui = self.ui
        self.rect = pygame.Rect(
            left + ui.px(12), screen.bottom - ui.px(SIZE[1]) - ui.px(12), ui.px(SIZE[0]), ui.px(SIZE[1])
        )

    def contains(self, point) -> bool:
        return bool(self.areas) and self.rect.collidepoint(point)

    def action_at(self, point) -> str | None:
        if not self.contains(point):
            return None
        return next((action for rect, action in reversed(self.areas) if rect.collidepoint(point)), "card")

    def draw(
        self,
        state: "GameState",
        unit: "Unit | None",
        hover: str | None,
        paths: "Paths | None",
        air_mode: str,
        place_name,
    ) -> None:
        self.areas = []
        if unit is None:
            return
        ui = self.ui
        faction = state.factions[unit.owner]
        rect = self.rect
        ui.shadow(rect, 4)
        pygame.draw.rect(ui.surface, style.PARCHMENT, rect)
        ui.frame(rect)
        self.areas.append((rect, "card"))
        pad = ui.px(style.PAD)
        header = pygame.Rect(rect.x, rect.y, rect.width, ui.px(32))
        pygame.draw.rect(ui.surface, style.SLATE, header)
        ui.swatch((header.x + pad + ui.px(4), header.centery), faction.color, 7)
        ui.text(
            unit_name(unit),
            (header.x + pad * 2 + ui.px(8), header.centery - ui.px(10)),
            style.BODY,
            style.ON_SLATE,
            bold=True,
            width=ui.px(250),
        )
        ui.text(
            place_name(unit.location),
            (header.right - ui.px(40), header.centery - ui.px(9)),
            style.SMALL,
            style.ON_SLATE_MUTED,
            align="right",
            width=ui.px(170),
        )
        self.areas.append((ui.close_button(header), "deselect"))
        top = header.bottom + ui.px(8)
        column = (rect.width - pad * 2) // 3
        strength = unit.hp / FULL_STRENGTH
        self._stat("Strength", f"{unit.hp:.1f} / {FULL_STRENGTH}", rect.x + pad, top)
        ui.progress(
            pygame.Rect(rect.x + pad, top + ui.px(38), column - pad, ui.px(6)),
            strength,
            style.GOOD if strength > 0.6 else style.WARN if strength > 0.3 else style.BAD,
        )
        if unit.kind == AIR:
            orders = "Sortie ready" if unit.remaining > 0 else "Sortie spent"
            self._stat("Orders", orders, rect.x + pad + column, top)
        else:
            self._stat("Movement", f"{unit.remaining:.1f} / {unit.allowance:g}", rect.x + pad + column, top)
        recovery = recovery_rate(state, unit) if unit.hp < FULL_STRENGTH else 0
        supply = "Supplied" if unit.supplied else "Cut off"
        detail = f"+{recovery:g} per turn" if recovery else ""
        self._stat(
            "Supply",
            supply,
            rect.x + pad + column * 2,
            top,
            style.GOOD if unit.supplied else style.BAD,
            detail,
        )
        upkeep = ", ".join(f"{amount:g} {resource}" for resource, amount in unit_upkeep(unit.kind).items())
        ui.hint(
            rect.inflate(0, -header.height),
            unit_name(unit),
            f"Attack {unit.attack:g}, defence {unit.defense:g}. Upkeep {upkeep} per turn. "
            "Tab cycles the units here; F centres this one.",
        )
        if unit.kind == AIR:
            self._missions(air_mode)
        elif paths and hover in paths.costs:
            ui.text(
                f"Route: {paths.costs[hover]:.1f} movement",
                (rect.right - pad, rect.bottom - ui.px(24)),
                style.SMALL,
                style.SLATE,
                align="right",
                bold=True,
            )

    def _stat(self, label: str, value: str, x: int, y: int, color=style.INK, detail: str = "") -> None:
        ui = self.ui
        ui.text(label.upper(), (x, y), 11, style.INK_MUTED, bold=True)
        ui.text(value, (x, y + ui.px(14)), style.BODY, color, bold=True)
        if detail:
            ui.text(detail, (x, y + ui.px(34)), style.SMALL, style.GOOD)

    def _missions(self, air_mode: str) -> None:
        ui = self.ui
        width, height = ui.px(96), ui.px(26)
        x = self.rect.right - ui.px(style.PAD) - width * 3 - ui.px(8)
        for i, mission in enumerate(MISSIONS):
            button = pygame.Rect(
                x + i * (width + ui.px(4)), self.rect.bottom - height - ui.px(8), width, height
            )
            ui.button(button, mission.title(), selected=mission == air_mode)
            ui.hint(button, mission.title(), MISSION_HELP.get(mission, ""))
            self.areas.append((button, "mission:" + mission))

    def mission_rect(self, mission: str) -> pygame.Rect | None:
        return next((rect for rect, action in self.areas if action == "mission:" + mission), None)
