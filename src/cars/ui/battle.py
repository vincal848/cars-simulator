"""Battle reports as tables: what decided the fight, and what it cost each side."""

from typing import TYPE_CHECKING

import pygame

from cars.ui.kit import style
from cars.ui.kit.grid import draw_grid

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.kit.ui import Ui

# Modifiers that changed nothing are left out of the table.
NEUTRAL = ("×1", "+0%")
STRENGTHS = ("Attack strength", "Defence strength")
DESTROYED = "destroyed"


def modifier_rows(factors: list) -> list[list]:
    """The modifiers that mattered, then both sides' strength in slate."""
    rows = [[label, value] for label, value in factors if value not in NEUTRAL and label not in STRENGTHS]
    rows += [[label, (value, style.SLATE)] for label, value in factors if label in STRENGTHS]
    return rows


def draw_modifiers(ui: "Ui", x: int, y: int, width: int, factors: list) -> int:
    rows = modifier_rows(factors)
    if not rows:
        return 0
    return draw_grid(ui, x, y, width, (("Modifier", None, "left"), ("Effect", 90, "right")), rows, 26)


def draw_losses(ui: "Ui", x: int, y: int, width: int, state: "GameState", losses: list) -> int:
    if not losses:
        return 0

    def nation(owner: str):
        faction = state.factions[owner]

        def paint(cell: pygame.Rect) -> None:
            ui.swatch((cell.x + ui.px(12), cell.centery), faction.color, 5)
            top = cell.centery - ui.font(style.SMALL).get_height() // 2
            ui.text(faction.name, (cell.x + ui.px(22), top), style.SMALL, style.INK, cell.width - ui.px(26))

        return paint

    rows = [
        [name, nation(owner), (f"−{lost}", style.BAD), (left, style.BAD if left == DESTROYED else style.INK)]
        for name, owner, lost, left in losses
    ]
    columns = (("Unit", None, "left"), ("Nation", None, "left"), ("Lost", 60, "right"), ("Left", 86, "right"))
    return draw_grid(ui, x, y, width, columns, rows, 26)
