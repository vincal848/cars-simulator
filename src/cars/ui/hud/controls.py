"""The bottom-right corner: map modes, world view, next unit and the End Turn button."""

import math
from typing import TYPE_CHECKING

import pygame

from cars.ui.kit import style
from cars.ui.map.map_view import DIPLOMATIC, POLITICAL, SUPPLY, TERRAIN

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.kit.ui import Ui

END_RADIUS = 46
BUTTON = 40
# (action, icon, title, help)
MODES = (
    (POLITICAL, "political", "Political map", "Nations in their colours, with their names. Shortcut: 1."),
    (TERRAIN, "terrain_mode", "Terrain map", "The land itself: plains, forests and mountains. Shortcut: 2."),
    (SUPPLY, "supply", "Supply map", "Your provinces in supply (green) or cut off (red). Shortcut: 3."),
    (
        DIPLOMATIC,
        "diplomacy",
        "Diplomatic map",
        "Who is at war with you (red), at peace (green) and your own land (blue). Shortcut: 4.",
    ),
)
EXTRAS = (
    ("home", "home", "World view", "Show the whole theatre. Shortcut: Home."),
    ("ready", "next", "Next unit", "Select and centre the next unit that still has orders. Shortcut: N."),
)


class Controls:
    def __init__(self, ui: "Ui") -> None:
        self.ui = ui
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.bar = pygame.Rect(0, 0, 0, 0)
        self.end_center = (0, 0)
        self.buttons: dict[str, pygame.Rect] = {}

    def layout(self, screen: pygame.Rect) -> None:
        ui = self.ui
        radius = ui.px(END_RADIUS)
        self.end_center = (screen.right - radius - ui.px(14), screen.bottom - radius - ui.px(14))
        size, gap = ui.px(BUTTON), ui.px(4)
        count = len(MODES) + len(EXTRAS)
        width = count * size + (count - 1) * gap + ui.px(12) + ui.px(16)
        self.bar = pygame.Rect(0, 0, width, size + ui.px(12))
        self.bar.bottomright = (self.end_center[0] - radius + ui.px(8), screen.bottom - ui.px(14))
        x = self.bar.x + ui.px(10)
        self.buttons = {}
        for i, (action, *_rest) in enumerate((*MODES, *EXTRAS)):
            if i == len(MODES):
                x += ui.px(12)  # A little space between the map modes and the other buttons.
            self.buttons[action] = pygame.Rect(x, self.bar.y + ui.px(6), size, size)
            x += size + gap
        end = pygame.Rect(0, 0, radius * 2, radius * 2)
        end.center = self.end_center
        self.rect = self.bar.union(end)

    @property
    def end_button(self) -> pygame.Rect:
        radius = self.ui.px(END_RADIUS)
        return pygame.Rect(self.end_center[0] - radius, self.end_center[1] - radius, radius * 2, radius * 2)

    def contains(self, point) -> bool:
        return self.bar.collidepoint(point) or math.dist(point, self.end_center) <= self.ui.px(END_RADIUS)

    def action_at(self, point) -> str | None:
        if math.dist(point, self.end_center) <= self.ui.px(END_RADIUS):
            return "end"
        return next((action for action, rect in self.buttons.items() if rect.collidepoint(point)), None)

    def draw(self, state: "GameState", player: str, mode: str, human_turn: bool) -> None:
        ui = self.ui
        pygame.draw.rect(ui.surface, style.SLATE, self.bar, border_radius=ui.px(6))
        pygame.draw.rect(ui.surface, style.BRASS, self.bar, max(1, ui.px(1)), border_radius=ui.px(6))
        ready = sum(u.owner == player and u.remaining > 0 for u in state.units.values())
        for action, icon, title, help_text in (*MODES, *EXTRAS):
            rect = self.buttons[action]
            badge = str(ready) if action == "ready" else None
            ui.icon_button(rect, icon, selected=action == mode, badge=badge)
            ui.hint(rect, title, help_text)
        self._end_button(human_turn)

    def _end_button(self, enabled: bool) -> None:
        ui = self.ui
        screen = ui.surface
        radius = ui.px(END_RADIUS)
        x, y = self.end_center
        hovered = enabled and math.dist(ui.mouse(), self.end_center) <= radius
        pygame.draw.circle(screen, style.SHADOW, (x + ui.px(2), y + ui.px(3)), radius + ui.px(3))
        pygame.draw.circle(screen, style.FRAME, self.end_center, radius + ui.px(3))
        pygame.draw.circle(screen, style.BRASS, self.end_center, radius)
        face = style.SLATE_LIGHT if hovered else style.SLATE if enabled else style.SLATE_DARK
        pygame.draw.circle(screen, face, self.end_center, radius - ui.px(5))
        pygame.draw.circle(screen, style.BRASS_LIGHT, self.end_center, radius - ui.px(9), max(1, ui.px(1)))
        ink = style.ON_SLATE if enabled else style.ON_SLATE_MUTED
        ui.icon("end", (x, y - ui.px(15)), 22, style.BRASS_LIGHT)
        font = ui.font(style.BODY, bold=True)
        for text, dy in (("END", 4), ("TURN", 20)):
            label = font.render(text, True, ink)
            screen.blit(label, label.get_rect(center=(x, y + ui.px(dy))))
        ui.hint(
            self.end_button,
            "End Turn",
            "Collect production, pay upkeep and let the seven rival nations act. Shortcut: Space."
            if enabled
            else "The rival nations are taking their turns.",
        )
