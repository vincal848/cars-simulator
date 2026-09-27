"""The strip along the top of the screen: nation, treasury, stockpiles and the date."""

from typing import TYPE_CHECKING

import pygame

from cars.sim.calendar import date_label, turn_phase
from cars.sim.economy import forecast, storage
from cars.sim.entities import RESOURCES
from cars.sim.upkeep import upkeep
from cars.ui.art.icons import draw_resource_icon
from cars.ui.palette import DIM, GOLD, GREEN, HOSTILE

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

TREASURY_X = 238
STOCKPILE_X = 318
STOCKPILE_WIDTH = 122


class TopBar:
    rect = pygame.Rect(0, 0, 1200, 44)
    date_rect = pygame.Rect(690, 0, 196, 44)

    def __init__(self, theme: "Theme") -> None:
        self.theme = theme

    def draw(self, state: "GameState", player: str) -> None:
        t = self.theme
        faction = state.factions[player]
        t.bar(self.rect)
        t.shield(12, 5, faction.color, scale=0.7)
        t.text(faction.name, 52, 12, t.heading, GOLD, width=176)
        t.seal("gold", (TREASURY_X + 10, 22), 22)
        t.text(f"{faction.gold:g}", TREASURY_X + 25, 12, t.body)
        t.hint(
            (TREASURY_X, 4, 72, 36),
            "Treasury",
            f"{faction.gold:g} gold. Use the Merchant Exchange (M) to trade fixed lots of wood, food "
            "and iron.",
        )
        self._draw_stockpiles(state, player)
        if state.player:
            self._draw_date(state)

    def _draw_stockpiles(self, state: "GameState", player: str) -> None:
        t = self.theme
        stock = state.factions[player].resources
        gains = forecast(state, player)
        costs = upkeep(state, player)
        limit = storage(state, player)
        for i, resource in enumerate(RESOURCES):
            left = STOCKPILE_X + i * STOCKPILE_WIDTH
            net = gains[resource] - costs[resource]
            full = stock[resource] >= limit
            draw_resource_icon(t.screen, resource, left, 11, 22)
            t.text(f"{stock[resource]:,.0f}", left + 27, 3, t.body)
            label = "Storage full" if full else f"{net:+.1f} / turn"
            t.text(label, left + 27, 23, t.small, HOSTILE if full or net < 0 else GREEN)
            t.hint(
                (left - 4, 4, STOCKPILE_WIDTH - 8, 36),
                resource.title(),
                f"Stock: {stock[resource]:g} of {limit} storage. Production {gains[resource]:.1f}, "
                f"upkeep {costs[resource]:.1f}: net {net:+.1f} on your faction turn. Production depends on "
                "controlled provinces, regional output and local improvements; occupied provinces yield "
                "half. Each city you hold adds storage and anything beyond it spoils. If upkeep cannot be "
                "paid, the units that need it lose strength.",
            )

    def _draw_date(self, state: "GameState") -> None:
        t = self.theme
        x = self.date_rect.x
        pygame.draw.line(t.screen, (103, 77, 57), (x, 8), (x, 36))
        t.seal("end", (x + 20, 22), 24)
        t.text(date_label(state.clock), x + 38, 3, t.heading, GOLD, width=150)
        _actor, completed = turn_phase(state)
        status = "Orders open" if state.active == state.player else f"Rivals {completed} / 7"
        t.text(f"Turn {state.clock['elapsed'] + 1}  /  {status}", x + 38, 25, t.small, DIM, width=150)
        t.hint(
            self.date_rect,
            "Campaign time",
            "One date spans your orders, resource settlement and seven rival turns. The calendar advances "
            "when control returns to you. There is no real-time deadline. Click for campaign stages.",
        )
