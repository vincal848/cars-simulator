"""The Crown Council: treasury, stockpiles, forces, map layers and End Turn."""

from typing import TYPE_CHECKING, ClassVar

import pygame

from cars.sim.calendar import date_label
from cars.sim.economy import forecast
from cars.sim.entities import AIR, FLEET, RESOURCES
from cars.ui.art.icons import draw_resource_icon
from cars.ui.art.ornament import branch, crown
from cars.ui.palette import DIM, GOLD, GREEN

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

LAYERS = ("land", "naval", "air", "supply")
LAYER_HELP = {
    "land": "Land forces and province movement. Shortcut: 1.",
    "naval": "Fleet movement and sea battles. Shortcut: 2.",
    "air": "Air coverage, strike, support and rebase orders. Shortcut: 3.",
    "supply": "Inspect connectivity to your controlled supply hubs. Shortcut: 4.",
}
FORCES = (("land", "Armies"), ("naval", "Fleets"), ("air", "Air"))
FORCES_HELP = "Your current forces. Open Military overview (U) for locations, strength and remaining orders."
BANNER = (72, 23, 35)


class CouncilPanel:
    rect = pygame.Rect(822, 374, 366, 356)
    home_button = pygame.Rect(842, 680, 124, 32)
    end_button = pygame.Rect(980, 680, 186, 32)
    ready_button = pygame.Rect(842, 656, 326, 20)
    view_buttons: ClassVar[dict[str, pygame.Rect]] = {
        name: pygame.Rect(842 + i * 82, 622, 76, 30) for i, name in enumerate(LAYERS)
    }

    def __init__(self, theme: "Theme") -> None:
        self.theme = theme

    def action_at(self, point) -> str | None:
        """The button under ``point``: "home", "end", "ready" or a map layer name."""
        if self.ready_button.collidepoint(point):
            return "ready"
        if self.home_button.collidepoint(point):
            return "home"
        for layer, rect in self.view_buttons.items():
            if rect.collidepoint(point):
                return layer
        if self.end_button.collidepoint(point):
            return "end"
        return None

    def draw(self, state: "GameState", player: str, layer: str) -> None:
        t = self.theme
        faction = state.factions[player]
        x, y = self.rect.topleft
        t.shadow(self.rect, 12, 5, 110)
        t.panel(self.rect)
        pygame.draw.rect(t.screen, BANNER, (x + 9, y + 10, self.rect.width - 18, 98), border_radius=3)
        t.rule(x + 18, y + 111, self.rect.width - 36)
        branch(t.screen, (self.rect.centerx - 26, y + 3), -1, 112)
        branch(t.screen, (self.rect.centerx + 26, y + 3), 1, 112)
        crown(t.screen, (self.rect.centerx, y - 4), 38)
        t.text("C . A . R . S .  /  CROWN COUNCIL", x + 25, y + 24, t.small, GOLD)
        t.shield(x + 23, y + 51, faction.color)
        t.text(faction.name, x + 80, y + 53, t.serif, width=260)
        t.text(date_label(state.clock), x + 82, y + 85, t.body, width=126)
        t.seal("gold", (x + 230, y + 93), 23)
        t.text(f"{faction.gold:g}", x + 246, y + 87, t.small, GOLD)
        t.hint(
            (x + 215, y + 78, 123, 27),
            "Treasury",
            f"{faction.gold:g} gold. Use the Merchant Exchange (M) to trade fixed lots of wood, food "
            "and iron.",
        )
        self._draw_stockpiles(state, player, x, y)
        self._draw_forces(state, player, x, y)
        for name, button in self.view_buttons.items():
            t.emblem_button(button, name.title(), name, layer == name, LAYER_HELP[name])
        t.emblem_button(
            self.home_button, "World", "home", help_text="Return the camera to the full Americas view."
        )
        t.emblem_button(
            self.end_button,
            "End Turn",
            "end",
            True,
            "Collect production and let the seven rival factions act. Shortcut: Space.",
        )
        ready = sum(u.owner == player and u.remaining > 0 for u in state.units.values())
        t.emblem_button(
            self.ready_button,
            f"{ready} ready / Next unit",
            "ready",
            help_text="Select and center the next unit with movement or a sortie remaining. Shortcut: N. "
            "Remaining orders do not guarantee a legal destination.",
        )

    def _draw_stockpiles(self, state: "GameState", player: str, x: int, y: int) -> None:
        t = self.theme
        stock = state.factions[player].resources
        gains = forecast(state, player)
        for i, resource in enumerate(RESOURCES):
            left = x + 20 + i * 110
            well = (left, y + 121, 104, 82)
            t.inset(well)
            draw_resource_icon(t.screen, resource, left + 9, y + 145, 23)
            t.text(resource.upper(), left + 10, y + 128, t.small, GOLD)
            t.text(f"{stock[resource]:,.0f}", left + 38, y + 142, t.number, width=61)
            t.text(f"+{gains[resource]:.1f} / turn", left + 10, y + 180, t.small, GREEN)
            t.hint(
                well,
                resource.title(),
                f"Stock: {stock[resource]:g}. Expected production: {gains[resource]:.1f} on your "
                "faction turn. Production depends on controlled provinces, regional output and local "
                "improvements.",
            )

    def _draw_forces(self, state: "GameState", player: str, x: int, y: int) -> None:
        t = self.theme
        own = [u for u in state.units.values() if u.owner == player]
        counts = {
            "land": sum(u.is_land for u in own),
            "naval": sum(u.kind == FLEET for u in own),
            "air": sum(u.kind == AIR for u in own),
        }
        for i, (layer, label) in enumerate(FORCES):
            left = x + 24 + i * 109
            t.seal(layer, (left + 10, y + 224), 24)
            t.text(f"{counts[layer]} {label}", left + 27, y + 216, t.small, DIM)
            t.hint((left - 2, y + 208, 106, 31), label, FORCES_HELP)
