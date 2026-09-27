"""The selected-unit card, air mission buttons and the status line along the bottom."""

from typing import TYPE_CHECKING, ClassVar

import pygame

from cars.sim.air import MISSIONS
from cars.sim.entities import AIR, FULL_STRENGTH
from cars.sim.recovery import recovery_rate
from cars.sim.regional import unit_name
from cars.ui.palette import DIM, GOLD, PAPER

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

CONTROLS_HINT = (
    "SCROLL Zoom   /   LEFT-DRAG Pan   /   RIGHT-CLICK Province window   /   ESC Close   /   F3 Debug"
)


class SelectionCard:
    """Details of the selected unit, or of the hovered province when nothing is selected."""

    air_buttons: ClassVar[dict] = {
        name: pygame.Rect(16 + i * 146, 638, 138, 34) for i, name in enumerate(MISSIONS)
    }

    def __init__(self, theme: "Theme") -> None:
        self.theme = theme

    def air_mode_at(self, point) -> str | None:
        return next((mode for mode, rect in self.air_buttons.items() if rect.collidepoint(point)), None)

    def draw(
        self,
        state: "GameState",
        unit: "Unit | None",
        hover: str | None,
        paths: "Paths | None",
        debug: bool,
        air_mode: str,
    ) -> None:
        t = self.theme
        if unit:
            t.panel((16, 682, 560, 51), True)
            t.text(unit_name(unit) + " / " + unit.id, 30, 688, t.heading, width=335)
            t.text("Tab: cycle / F: focus / U: overview", 590, 707, t.small, DIM, width=215)
            recovery = recovery_rate(state, unit) if unit.hp < FULL_STRENGTH else 0
            healing = f"  /  Recovering +{recovery:g}" if recovery else ""
            if unit.kind == AIR:
                sortie = "Sortie ready" if unit.remaining > 0 else "Sortie spent"
                status = f"{sortie} / Strength {unit.hp:.1f}/10 / {air_mode.title()}"
                for mode, rect in self.air_buttons.items():
                    t.button(rect, mode.title(), air_mode == mode)
            else:
                status = f"Movement {unit.remaining:.1f}/{unit.allowance:.0f}  /  Strength {unit.hp:.1f}/10"
            t.text(status + healing, 30, 714, t.small, DIM, width=340)
            if paths and hover in paths.costs:
                t.text(f"Route: {paths.costs[hover]:.2f} MP", 376, 691, t.body, GOLD)
                if debug:
                    t.text(hover, 376, 714, t.small, DIM, width=186)
        elif hover in state.provinces:
            province = state.provinces[hover]
            t.panel((16, 690, 360, 40), True)
            t.text(province.name + " / " + province.terrain, 29, 700, t.body, width=331)


def draw_status_bar(theme: "Theme", message: str) -> None:
    theme.panel((0, 742, 1200, 38))
    theme.text(message, 17, 745, theme.small, PAPER, width=1160)
    theme.text(CONTROLS_HINT, 17, 762, theme.small, DIM)
