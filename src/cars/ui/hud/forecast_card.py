"""The order forecast shown beside the pointer while hovering an attack target.

It runs the real rules on a copy of the state, so it predicts exactly what the
order would do under current conditions.
"""

from typing import TYPE_CHECKING

import pygame

from cars.sim.entities import BALLOON, FLEET
from cars.sim.forecast import MOVE, forecast_order, signature
from cars.ui.battle import draw_modifiers, modifier_rows
from cars.ui.kit import style

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.kit.ui import Ui

WIDTH = 330
TITLE_HEIGHT = 40


class ForecastCard:
    def __init__(self, ui: "Ui") -> None:
        self.ui = ui
        # Forecasts deep-copy the state, so reuse one until anything relevant changes.
        self.key: tuple | None = None
        self.result: dict | None = None
        self.rect: pygame.Rect | None = None

    def draw(
        self,
        state: "GameState",
        unit: "Unit | None",
        target: str | None,
        paths: "Paths | None",
    ) -> None:
        self.rect = None
        # Balloon ascents fight no battles, so only attacks get a forecast.
        if not unit or unit.owner != state.active or not target or unit.kind == BALLOON:
            return
        if not self._is_attack(state, unit, target, paths):
            return
        key = (unit.id, target, signature(state))
        if self.key != key:
            self.key = key
            self.result = forecast_order(state, unit.id, target, MOVE)
        self._draw_card(state, unit, target, self.result)

    @staticmethod
    def _is_attack(state: "GameState", unit: "Unit", target: str, paths: "Paths | None") -> bool:
        if not paths or target not in paths.costs:
            return False
        if target in state.provinces and state.at_war(unit.owner, state.provinces[target].controller):
            return True
        return any(
            u.location == target and u.kind == FLEET and state.at_war(unit.owner, u.owner)
            for u in state.units.values()
        )

    def _draw_card(self, state: "GameState", unit: "Unit", target: str, result: dict) -> None:
        ui = self.ui
        modifiers = modifier_rows(result["factors"])
        line = ui.px(24)
        width = ui.px(WIDTH)
        height = ui.px(TITLE_HEIGHT) + line * 4 + ui.px(26) * (len(modifiers) + 1) + ui.px(34)
        mouse_x, mouse_y = ui.mouse()
        offset = ui.px(22)
        screen = ui.screen
        x = (
            mouse_x + offset
            if mouse_x + offset + width < screen.right - ui.px(300)
            else mouse_x - width - offset
        )
        y = (
            mouse_y + offset
            if mouse_y + offset + height < screen.bottom - ui.px(20)
            else mouse_y - height - offset
        )
        rect = pygame.Rect(x, y, width, height).clamp(screen.inflate(-ui.px(16), -ui.px(16)))
        self.rect = rect
        inner = ui.panel(rect, "Order forecast", "war")
        success = "captured" in result["message"] or "destroyed" in result["message"].lower()
        ui.text(
            result["message"],
            (inner.x, inner.y),
            style.BODY,
            style.GOOD if success else style.INK,
            width=inner.width,
            bold=True,
        )
        rows = (
            (
                "Your losses",
                f"{result['own_loss']:.1f} strength",
                style.BAD if result["own_loss"] else style.INK,
            ),
            (
                "Enemy losses",
                f"{result['enemy_loss']:.1f} strength",
                style.GOOD if result["enemy_loss"] else style.INK,
            ),
            ("Units destroyed", str(result["destroyed"]), style.INK),
        )
        for i, (label, value, color) in enumerate(rows):
            top = inner.y + line * (i + 1) + ui.px(2)
            ui.text(label, (inner.x, top), style.SMALL, style.INK_MUTED)
            ui.text(value, (inner.right, top), style.SMALL, color, align="right")
        draw_modifiers(ui, inner.x, inner.y + line * 4 + ui.px(6), inner.width, result["factors"])
