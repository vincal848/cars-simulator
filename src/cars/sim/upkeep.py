"""Upkeep: every unit consumes resources at the end of its faction's turn.

When a stockpile cannot cover the bill it is emptied and every unit that needed
that resource loses strength, so armies are limited by what the realm produces.
"""

from typing import TYPE_CHECKING

from cars.sim.defines import DEFINES
from cars.sim.economy import forecast
from cars.sim.entities import RESOURCES
from cars.sim.journal import record
from cars.sim.supply import refresh_supply

if TYPE_CHECKING:
    from cars.sim.state import GameState

RULES = DEFINES.upkeep


def unit_upkeep(kind: str) -> dict[str, float]:
    return dict(RULES.per_unit.get(kind, {}))


def upkeep(state: "GameState", owner: str) -> dict[str, float]:
    """Resources ``owner``'s units consume each turn."""
    total = dict.fromkeys(RESOURCES, 0.0)
    for unit in state.units.values():
        if unit.owner == owner:
            for resource, amount in unit_upkeep(unit.kind).items():
                total[resource] += amount
    return total


def net_income(state: "GameState", owner: str) -> dict[str, float]:
    """Production minus upkeep: the change in each stockpile per turn."""
    costs = upkeep(state, owner)
    return {resource: gain - costs[resource] for resource, gain in forecast(state, owner).items()}


def pay_upkeep(state: "GameState", owner: str) -> list[str]:
    """Deduct upkeep; returns the resources that ran short."""
    stock = state.factions[owner].resources
    short = []
    for resource, cost in upkeep(state, owner).items():
        if stock[resource] >= cost:
            stock[resource] -= cost
        else:
            stock[resource] = 0
            short.append(resource)
    if short:
        _suffer_shortage(state, owner, short)
    return short


def _suffer_shortage(state: "GameState", owner: str, short: list[str]) -> None:
    affected = [
        unit
        for unit in state.units.values()
        if unit.owner == owner and any(resource in unit_upkeep(unit.kind) for resource in short)
    ]
    lost = []
    for unit in affected:
        unit.hp -= RULES.shortfall_attrition
        if unit.hp <= 0:
            del state.units[unit.id]
            lost.append(unit.id)
    state.reindex_units()
    refresh_supply(state)
    details = [f"Short of {', '.join(short)}: {len(affected)} units lost strength."]
    details += [f"{unit_id}: disbanded" for unit_id in lost]
    record(state, "upkeep", "Supplies ran short.", details=details, participants=[owner])
