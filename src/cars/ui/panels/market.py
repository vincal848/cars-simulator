"""The Merchant Exchange: prices, stock and trades for each resource, in one table."""

import pygame

from cars.sim.entities import RESOURCES
from cars.sim.market import BUY, RULES, SELL, quote, treasury_income
from cars.ui.frames import DockedPanel
from cars.ui.kit import style
from cars.ui.kit.grid import draw_grid, section


class MarketPanel(DockedPanel):
    name = "market"
    title = "Merchant Exchange"
    icon = "market"
    width = 560

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        state = self.state
        owner = self.game.campaign.player
        faction = state.factions[owner]
        x, y, width = rect.x, rect.y, rect.width
        ui.text(f"{faction.gold:,.0f} gold", (x, y), style.TITLE - 2, style.SLATE, bold=True)
        ui.text(
            f"+{treasury_income(state, owner)} a turn from your cities",
            (x, y + ui.px(30)),
            style.BODY,
            style.INK_MUTED,
        )
        y += ui.px(60)
        y += ui.paragraph(
            f"Each contract trades a lot of {RULES.lot_size}. Buying drains the merchants' stock and "
            "raises the price; selling refills it at a discount.",
            pygame.Rect(x, y, width, ui.px(60)),
            style.BODY,
        ) + ui.px(8)
        y += section(ui, "Contracts", x, y, width)
        rows, hints = [], []
        for resource in RESOURCES:
            buy_price, buy_error = quote(state, owner, resource, BUY)
            sell_price, sell_error = quote(state, owner, resource, SELL)

            def trade_cell(area, resource=resource, side=BUY, price=buy_price, error=buy_error):
                button = area.inflate(-ui.px(8), -ui.px(6))
                self.button(
                    button,
                    f"{side.title()} · {price}",
                    f"trade:{resource}:{side}",
                    enabled=not error,
                    kind="primary" if side == BUY else "secondary",
                )

            def sell_cell(area, resource=resource, price=sell_price, error=sell_error):
                trade_cell(area, resource, SELL, price, error)

            rows.append(
                [
                    resource.title(),
                    f"{faction.resources[resource]:,.0f}",
                    f"{state.market[resource]} / {RULES.capacity}",
                    trade_cell,
                    sell_cell,
                ]
            )
            reasons = "; ".join(
                filter(None, (buy_error and "Buy: " + buy_error, sell_error and "Sell: " + sell_error))
            )
            hints.append(
                (
                    resource.title(),
                    reasons
                    or f"Buy {RULES.lot_size} for {buy_price} gold, "
                    f"or sell {RULES.lot_size} for {sell_price}.",
                )
            )
        columns = [
            ("Resource", None, "left"),
            ("Yours", 70, "right"),
            ("Merchants", 96, "right"),
            ("", 118, "center"),
            ("", 118, "center"),
        ]
        y += draw_grid(ui, x, y, width, columns, rows, row_height=36, hints=hints)
        y += ui.px(10)
        ui.text(
            f"Merchant stock grows by {RULES.replenishment} of each resource every round.",
            (x, y),
            style.SMALL,
            style.INK_MUTED,
        )
        y += ui.px(24)
        if self.notice:
            ui.text(self.notice, (x, y), style.BODY, style.SLATE, width=width)
            y += ui.px(24)
        return y - rect.y

    def act(self, action: str) -> None:
        verb, _, rest = action.partition(":")
        if verb == "trade":
            resource, side = rest.split(":")
            _, self.notice = self.game.campaign.trade(resource, side)
            self.game.view.message = self.notice
