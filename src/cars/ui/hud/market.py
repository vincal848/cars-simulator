"""The Merchant Exchange window. Prices shown are always the total for a lot of ten."""

from typing import TYPE_CHECKING, ClassVar

import pygame

from cars.sim.entities import RESOURCES
from cars.sim.market import BUY, RULES, SELL, quote, treasury_income
from cars.ui.art.icons import draw_resource_icon

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

DEFAULT_RECEIPT = "Manual contracts only. Delivery is immediate."


class MarketPanel:
    rect = pygame.Rect(220, 165, 580, 446)
    close_button = pygame.Rect(762, 177, 26, 26)
    trade_buttons: ClassVar[dict] = {
        (resource, side): pygame.Rect(465 + j * 154, 297 + i * 86, 146, 34)
        for i, resource in enumerate(RESOURCES)
        for j, side in enumerate((BUY, SELL))
    }

    def __init__(self, theme: "Theme") -> None:
        self.theme = theme
        self.open = False
        self.receipt = DEFAULT_RECEIPT

    def trade_at(self, point) -> tuple[str, str] | None:
        return next((trade for trade, rect in self.trade_buttons.items() if rect.collidepoint(point)), None)

    def draw(self, state: "GameState", owner: str) -> None:
        t = self.theme
        t.dim_screen((8, 13, 17, 150))
        t.panel(self.rect)
        x, y = self.rect.topleft
        faction = state.factions[owner]
        t.text("The Merchant Exchange", x + 22, y + 16, t.serif)
        t.button(self.close_button, "×")
        income = treasury_income(state, owner)
        t.text(f"Treasury: {faction.gold:g} gold    Income: +{income} per turn", x + 22, y + 51, t.heading)
        t.text(
            "Each contract trades exactly 10. Prices below are the full lot price.", x + 22, y + 81, t.body
        )
        t.text(self.receipt, x + 22, y + 385, t.small, width=532)
        for i, resource in enumerate(RESOURCES):
            top = y + 112 + i * 86
            t.inset((x + 18, top, 544, 76))
            draw_resource_icon(t.screen, resource, x + 30, top + 15, 30)
            t.text(resource.title(), x + 74, top + 8, t.heading)
            t.text(f"Yours: {faction.resources[resource]:g}", x + 74, top + 34, t.small)
            t.text(f"Merchant: {state.market[resource]} / {RULES.capacity}", x + 74, top + 52, t.small)
            for side in (BUY, SELL):
                total, error = quote(state, owner, resource, side)
                button = self.trade_buttons[(resource, side)]
                t.button(button, f"{side.title()} 10 / {total} gold", enabled=not error)
                if error and button.collidepoint(t.mouse_pos()):
                    t.text(error, x + 22, y + 368, t.small, width=532)
        t.text(
            f"Stock replenishes by {RULES.replenishment} per resource each round, up to {RULES.capacity}.",
            x + 22,
            y + 412,
            t.small,
        )
