"""The merchant exchange: manual fixed-lot contracts against a bounded inventory.

Gold is a trading currency rather than a fourth production resource. Stock is
shared by all factions and replenishes once per round.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cars.paths import load_content

if TYPE_CHECKING:
    from cars.sim.state import GameState

BUY = "buy"
SELL = "sell"


@dataclass(frozen=True)
class MarketRules:
    lot_size: int
    starting_gold: int
    gold_per_city: int
    starting_stock: int
    capacity: int
    replenishment: int
    base_prices: dict[str, int]
    minimum_price: int
    price_step: int
    stock_step: int
    sell_ratio: float


RULES = MarketRules(**load_content("common", "market.json"))


def new_stock() -> dict[str, int]:
    return dict.fromkeys(RULES.base_prices, RULES.starting_stock)


def price(state: "GameState", resource: str, side: str) -> int:
    """Total price of one lot. Scarce stock raises the price in steps."""
    stock = state.market[resource]
    # Sales are quoted at the resulting stock level, so buying then selling never profits.
    reference = stock if side == BUY else stock + RULES.lot_size
    scarcity = (RULES.starting_stock - reference) // RULES.stock_step
    base = max(RULES.minimum_price, RULES.base_prices[resource] + RULES.price_step * scarcity)
    if side == BUY:
        return base
    return max(1, int(base * RULES.sell_ratio))


def quote(state: "GameState", owner: str, resource: str, side: str) -> tuple[int, str]:
    """Lot price and the reason the trade is refused (empty when allowed)."""
    if owner not in state.factions or resource not in RULES.base_prices or side not in (BUY, SELL):
        return 0, "Invalid contract."
    total = price(state, resource, side)
    if state.active != owner:
        return total, "Trade on your own turn."
    faction = state.factions[owner]
    if side == BUY:
        if state.market[resource] < RULES.lot_size:
            return total, "Merchant stock is too low."
        if faction.gold < total:
            return total, "Not enough gold."
    else:
        if faction.resources[resource] < RULES.lot_size:
            return total, "You need a full lot of 10."
        if state.market[resource] + RULES.lot_size > RULES.capacity:
            return total, "Merchant storage is full."
    return total, ""


def trade(state: "GameState", owner: str, resource: str, side: str) -> tuple[bool, str]:
    total, error = quote(state, owner, resource, side)
    if error:
        return False, error
    faction = state.factions[owner]
    direction = 1 if side == BUY else -1
    faction.resources[resource] += direction * RULES.lot_size
    state.market[resource] -= direction * RULES.lot_size
    faction.gold -= direction * total
    verb = "Bought" if side == BUY else "Sold"
    return True, f"{verb} {RULES.lot_size} {resource} for {total} gold. Delivered immediately."


def replenish(state: "GameState") -> None:
    for resource in state.market:
        state.market[resource] = min(RULES.capacity, state.market[resource] + RULES.replenishment)


def treasury_income(state: "GameState", owner: str) -> int:
    held = sum(state.provinces[c.province].controller == owner for c in state.cities.values())
    return RULES.gold_per_city * held
