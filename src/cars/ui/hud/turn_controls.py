"""The corner cluster: a large End Turn button, the map layers, next unit and world view."""

import math
from typing import TYPE_CHECKING, ClassVar

import pygame

from cars.sim.entities import AIR, FLEET
from cars.ui.palette import GOLD, PAPER

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
END_CENTER = (1134, 664)
END_RADIUS = 54
RING = (26, 15, 18)
FACE = (122, 35, 47)
FACE_HOVER = (148, 45, 57)


class TurnControls:
    rect = pygame.Rect(924, 606, 270, 132)
    plate = pygame.Rect(924, 610, 176, 124)
    end_button = pygame.Rect(
        END_CENTER[0] - END_RADIUS, END_CENTER[1] - END_RADIUS, 2 * END_RADIUS, 2 * END_RADIUS
    )
    home_button = pygame.Rect(934, 620, 136, 28)
    view_buttons: ClassVar[dict[str, pygame.Rect]] = {
        name: pygame.Rect(934 + i * 35, 656, 31, 31) for i, name in enumerate(LAYERS)
    }
    ready_button = pygame.Rect(934, 696, 136, 28)

    def __init__(self, theme: "Theme") -> None:
        self.theme = theme

    def action_at(self, point) -> str | None:
        """The control under ``point``: "home", "end", "ready" or a map layer name."""
        if math.dist(point, END_CENTER) <= END_RADIUS:
            return "end"
        if self.ready_button.collidepoint(point):
            return "ready"
        if self.home_button.collidepoint(point):
            return "home"
        return next((layer for layer, rect in self.view_buttons.items() if rect.collidepoint(point)), None)

    def draw(self, state: "GameState", player: str, layer: str) -> None:
        t = self.theme
        t.shadow(self.plate, 8, 4, 90)
        t.panel(self.plate)
        t.emblem_button(
            self.home_button, "World view", "home", help_text="Return the camera to the full Americas view."
        )
        own = [u for u in state.units.values() if u.owner == player]
        counts = {
            "land": sum(u.is_land for u in own),
            "naval": sum(u.kind == FLEET for u in own),
            "air": sum(u.kind == AIR for u in own),
        }
        for name, rect in self.view_buttons.items():
            self._draw_layer_button(rect, name, name == layer, counts.get(name))
        ready = sum(u.remaining > 0 for u in own)
        t.emblem_button(
            self.ready_button,
            f"{ready} ready / Next",
            "ready",
            help_text="Select and center the next unit with movement or a sortie remaining. Shortcut: N. "
            "Remaining orders do not guarantee a legal destination.",
        )
        self._draw_end_button()

    def _draw_layer_button(self, rect: pygame.Rect, name: str, active: bool, count: int | None) -> None:
        t = self.theme
        center = rect.center
        radius = rect.width // 2
        hovered = rect.collidepoint(t.mouse_pos())
        pygame.draw.circle(t.screen, (12, 14, 17), (center[0], center[1] + 2), radius)
        pygame.draw.circle(t.screen, (73, 39, 42) if active or hovered else (38, 29, 33), center, radius)
        pygame.draw.circle(t.screen, GOLD if active else (103, 77, 57), center, radius, 2 if active else 1)
        t.seal(name, center, 22)
        if count is not None:
            label = t.small.render(str(count), True, PAPER)
            badge = label.get_rect(center=(rect.right - 3, rect.bottom - 4)).inflate(6, 0)
            pygame.draw.rect(t.screen, RING, badge, border_radius=6)
            t.screen.blit(label, label.get_rect(center=badge.center))
        t.hint(rect, name.title(), LAYER_HELP[name])

    def _draw_end_button(self) -> None:
        t = self.theme
        screen = t.screen
        hovered = math.dist(t.mouse_pos(), END_CENTER) <= END_RADIUS
        x, y = END_CENTER
        pygame.draw.circle(screen, (8, 10, 12), (x + 2, y + 4), END_RADIUS + 3)
        pygame.draw.circle(screen, RING, END_CENTER, END_RADIUS + 3)
        pygame.draw.circle(screen, (149, 111, 61), END_CENTER, END_RADIUS)
        pygame.draw.circle(screen, FACE_HOVER if hovered else FACE, END_CENTER, END_RADIUS - 5)
        # A lighter upper half suggests a domed, lit face.
        highlight = pygame.Surface((2 * END_RADIUS, END_RADIUS), pygame.SRCALPHA)
        pygame.draw.ellipse(highlight, (255, 226, 170, 26), (10, 8, 2 * END_RADIUS - 20, END_RADIUS))
        screen.blit(highlight, (x - END_RADIUS, y - END_RADIUS))
        pygame.draw.circle(screen, GOLD, END_CENTER, END_RADIUS - 5, 2)
        pygame.draw.circle(screen, (98, 68, 46), END_CENTER, END_RADIUS - 11, 1)
        t.seal("end", (x, y - 22), 26)
        t.centered("END", x, y - 6, t.heading, PAPER)
        t.centered("TURN", x, y + 13, t.heading, PAPER)
        t.hint(
            self.end_button,
            "End Turn",
            "Collect production and let the seven rival factions act. Shortcut: Space.",
        )
