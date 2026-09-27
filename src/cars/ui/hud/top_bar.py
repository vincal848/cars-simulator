"""The strip along the top of the screen: nation, treasury, stockpiles and the date."""

from typing import TYPE_CHECKING

import pygame

from cars.sim.calendar import date_label, turn_phase
from cars.sim.economy import forecast, storage
from cars.sim.entities import RESOURCES
from cars.sim.market import treasury_income
from cars.sim.upkeep import upkeep
from cars.ui.art.icons import draw_resource_icon
from cars.ui.kit import style

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.kit.ui import Ui

GOOD_ON_SLATE = (150, 210, 150)
BAD_ON_SLATE = (236, 140, 120)


class TopBar:
    def __init__(self, ui: "Ui") -> None:
        self.ui = ui
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.date_rect = pygame.Rect(0, 0, 0, 0)

    def layout(self, screen: pygame.Rect) -> None:
        self.rect = pygame.Rect(0, 0, screen.width, self.ui.px(style.BAR_HEIGHT))
        width = self.ui.px(230)
        self.date_rect = pygame.Rect(screen.right - width, 0, width, self.rect.height)

    def draw(self, state: "GameState", player: str) -> None:
        ui = self.ui
        faction = state.factions[player]
        ui.bar(self.rect)
        middle = self.rect.centery
        ui.swatch((ui.px(24), middle), faction.color, 10)
        ui.text(
            faction.name,
            (ui.px(42), middle - ui.font(style.HEADING, True).get_height() // 2),
            style.HEADING,
            style.ON_SLATE,
            width=ui.px(210),
            bold=True,
        )
        x = ui.px(270)
        x = self._treasury(state, player, x)
        for resource in RESOURCES:
            x = self._stockpile(state, player, resource, x)
        if state.player:
            self._date(state)

    def _figure(self, x: int, value: str, change: str, change_color, icon_draw) -> int:
        """An icon, a value and its change per turn; returns the x after it."""
        ui = self.ui
        icon_draw(x)
        top = self.rect.centery - ui.px(15)
        value_rect = ui.text(value, (x + ui.px(28), top), style.NUMBER, style.ON_SLATE, bold=True)
        change_rect = ui.text(change, (x + ui.px(28), top + ui.px(18)), style.SMALL, change_color)
        return max(value_rect.right, change_rect.right) + ui.px(26)

    def _treasury(self, state: "GameState", player: str, x: int) -> int:
        ui = self.ui
        faction = state.factions[player]
        income = treasury_income(state, player)
        start = x
        x = self._figure(
            x,
            f"{faction.gold:,.0f}",
            f"+{income} / turn",
            GOOD_ON_SLATE,
            lambda left: ui.icon("gold", (left + ui.px(11), self.rect.centery), 22, style.ACCENT_LIGHT),
        )
        ui.hint(
            pygame.Rect(start, 0, x - start, self.rect.height),
            "Treasury",
            f"{faction.gold:g} gold, +{income} each turn from the cities you hold. Spend it at the "
            "Merchant Exchange (M) on lots of wood, food and iron.",
        )
        return x

    def _stockpile(self, state: "GameState", player: str, resource: str, x: int) -> int:
        ui = self.ui
        stock = state.factions[player].resources
        gains = forecast(state, player)
        costs = upkeep(state, player)
        limit = storage(state, player)
        net = gains[resource] - costs[resource]
        full = stock[resource] >= limit
        change = "storage full" if full else f"{net:+.1f} / turn"
        start = x
        icon_size = ui.px(20)
        x = self._figure(
            x,
            f"{stock[resource]:,.0f}",
            change,
            BAD_ON_SLATE if full or net < 0 else GOOD_ON_SLATE,
            lambda left: draw_resource_icon(
                ui.surface, resource, left, self.rect.centery - icon_size // 2, icon_size
            ),
        )
        ui.hint(
            pygame.Rect(start, 0, x - start, self.rect.height),
            resource.title(),
            f"{stock[resource]:g} in store of {limit} capacity.\n"
            f"Production {gains[resource]:+.1f}, upkeep {-costs[resource]:+.1f}: {net:+.1f} each turn.\n"
            "Production comes from the provinces you hold, their resource sites and buildings; "
            "occupied provinces yield half. Each city adds storage and anything beyond it spoils. "
            "If upkeep cannot be paid, the units that need it lose strength.",
        )
        return x

    def _date(self, state: "GameState") -> None:
        ui = self.ui
        rect = self.date_rect
        if ui.hovered(rect):
            pygame.draw.rect(ui.surface, style.SLATE_LIGHT, rect)
        pygame.draw.line(
            ui.surface, style.SLATE_LIGHT, rect.topleft, (rect.x, rect.bottom - ui.px(3)), max(1, ui.px(1))
        )
        ui.icon("end", (rect.x + ui.px(22), rect.centery), 22, style.ACCENT_LIGHT)
        top = rect.centery - ui.px(16)
        ui.text(date_label(state.clock), (rect.x + ui.px(42), top), style.HEADING, style.ON_SLATE, bold=True)
        _actor, completed = turn_phase(state)
        status = "Your orders" if state.active == state.player else f"Rivals moving, {completed} of 7"
        ui.text(
            f"Turn {state.clock['elapsed'] + 1}  ·  {status}",
            (rect.x + ui.px(42), top + ui.px(19)),
            style.SMALL,
            style.ON_SLATE_MUTED,
        )
        ui.hint(
            rect,
            "Campaign calendar",
            "Each date covers your orders, then the seven rival nations' turns. Click to open the "
            "calendar and the path to dominion (T).",
        )
