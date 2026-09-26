"""The order forecast shown while hovering an attack target, computed with the real rules."""

from typing import TYPE_CHECKING

import pygame

from cars.sim.air import coverage
from cars.sim.entities import AIR, FLEET
from cars.sim.forecast import MOVE, forecast_order, signature
from cars.ui.palette import DIM, GOLD

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

SIZE = (358, 147)


class ForecastCard:
    def __init__(self, theme: "Theme") -> None:
        self.theme = theme
        # Forecasts deep-copy the state, so reuse one until anything relevant changes.
        self.key: tuple | None = None
        self.result: dict | None = None

    def draw(
        self,
        state: "GameState",
        unit: "Unit | None",
        target: str | None,
        paths: "Paths | None",
        air_mode: str,
    ) -> None:
        if not unit or unit.owner != state.active or not target:
            return
        mode = air_mode if unit.kind == AIR else MOVE
        if mode == MOVE and not self._is_attack(state, unit, target, paths):
            return
        if unit.kind == AIR and (target not in coverage(state, unit) or target == unit.location):
            return
        key = (unit.id, target, mode, signature(state))
        if self.key != key:
            self.key = key
            self.result = forecast_order(state, unit.id, target, mode)
        self._draw_card(state, unit, target, self.result)

    @staticmethod
    def _is_attack(state: "GameState", unit: "Unit", target: str, paths: "Paths | None") -> bool:
        if not paths or target not in paths.costs:
            return False
        if target in state.provinces and state.provinces[target].controller != unit.owner:
            return True
        return any(
            u.location == target and u.owner != unit.owner and u.kind == FLEET for u in state.units.values()
        )

    def _draw_card(self, state: "GameState", unit: "Unit", target: str, result: dict) -> None:
        t = self.theme
        mouse_x, mouse_y = t.mouse_pos()
        x = mouse_x + 20 if mouse_x < 440 else mouse_x - 378
        y = mouse_y + 24 if mouse_y < 480 else mouse_y - 163
        x = max(12, min(822, x))
        y = max(112, min(575, y))
        t.panel(pygame.Rect(x, y, *SIZE))
        t.text("ORDER FORECAST", x + 12, y + 9, t.small, GOLD)
        t.text(result["message"], x + 12, y + 32, t.body, width=334)
        t.text(
            f"Your losses: {result['own_loss']:.1f} / Enemy: {result['enemy_loss']:.1f}",
            x + 12,
            y + 58,
            t.body,
        )
        t.text(f"Enemy units destroyed: {result['destroyed']}", x + 12, y + 81, t.small, DIM)
        if target in state.provinces:
            supply = "Supplied" if unit.supplied else "Cut off from supply"
            t.text(state.provinces[target].terrain.title() + " / " + supply, x + 12, y + 103, t.small, GOLD)
        t.text("Current conditions / click target to issue order", x + 12, y + 126, t.small, DIM)
