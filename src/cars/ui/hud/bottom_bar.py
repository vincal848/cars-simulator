"""The selected-unit card, air mission buttons and the status line along the bottom."""

import math
from typing import TYPE_CHECKING, ClassVar

import pygame

from cars.sim.air import MISSIONS
from cars.sim.entities import AIR, FULL_STRENGTH
from cars.sim.recovery import recovery_rate
from cars.sim.regional import unit_name
from cars.ui.art.emblem import americas_emblem
from cars.ui.palette import DIM, GOLD, PAPER

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

CONTROLS_HINT = (
    "SCROLL Zoom   /   LEFT-DRAG Pan   /   RIGHT-CLICK Province window   /   ESC Close   /   F3 Debug"
)
EMBLEM_RECT = pygame.Rect(16, 16, 304, 98)
COMPASS_CENTER = (92, 634)


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


def draw_emblem(theme: "Theme") -> None:
    key = ("emblem", theme.font_index)
    if key not in theme.cache:
        theme.cache[key] = americas_emblem(theme.font(43), theme.font(22))
    theme.screen.blit(theme.cache[key], EMBLEM_RECT.topleft)


def draw_compass(theme: "Theme") -> None:
    x, y = COMPASS_CENTER
    s = theme.screen
    pygame.draw.circle(s, (60, 82, 86), (x, y), 34, 1)
    pygame.draw.circle(s, (60, 82, 86), (x, y), 29, 1)
    for i in range(8):
        a = i * math.pi / 4
        length = 30 if i % 2 == 0 else 19
        tip = (x + math.sin(a) * length, y - math.cos(a) * length)
        side_a = (x + math.cos(a) * 5, y + math.sin(a) * 5)
        side_b = (x - math.cos(a) * 5, y - math.sin(a) * 5)
        pygame.draw.polygon(s, (139, 141, 113) if i % 2 == 0 else (62, 86, 89), [(x, y), tip, side_a])
        pygame.draw.polygon(s, (66, 93, 96), [(x, y), tip, side_b])
    theme.text("N", x - 5, y - 52, theme.heading, GOLD)
