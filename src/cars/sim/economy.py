"""Resource production, collected at the end of each faction's turn.

Occupied provinces (controlled but owned by someone else) yield only part of
their output, and each stockpile holds only as much as the faction's cities
can store; anything beyond that spoils.
"""

from typing import TYPE_CHECKING

from cars.sim.buildings import BUILDINGS
from cars.sim.defines import DEFINES
from cars.sim.entities import RESOURCES

if TYPE_CHECKING:
    from cars.sim.entities import Province
    from cars.sim.state import GameState

RULES = DEFINES.economy


def _yield(province: "Province") -> float:
    return 1 if province.owner == province.controller else RULES.occupied_yield


def forecast(state: "GameState", owner: str) -> dict[str, float]:
    """Expected income. Regional output is shared by controlled-province share;
    resource sites and buildings are local."""
    gains = dict.fromkeys(RESOURCES, 0.0)
    for region in state.regions.values():
        held = [state.provinces[p] for p in region.provinces if state.provinces[p].controller == owner]
        share = sum(_yield(p) for p in held) / len(region.provinces)
        for resource in RESOURCES:
            gains[resource] += region.production[resource] * share
            gains[resource] += sum(p.resource_sites.get(resource, 0) * _yield(p) for p in held)
    for province in state.provinces.values():
        if province.controller != owner:
            continue
        for kind, level in province.buildings.items():
            spec = BUILDINGS[kind]
            if spec.produces:
                gains[spec.resource] += level * spec.output * _yield(province)
    return gains


def storage(state: "GameState", owner: str) -> int:
    """The most of each resource ``owner`` can stockpile."""
    cities = sum(state.provinces[city.province].controller == owner for city in state.cities.values())
    return RULES.storage_base + RULES.storage_per_city * cities


def produce(state: "GameState", owner: str) -> dict[str, float]:
    gains = forecast(state, owner)
    stock = state.factions[owner].resources
    limit = storage(state, owner)
    for resource, amount in gains.items():
        stock[resource] = max(stock[resource], min(limit, stock[resource] + amount))
    return gains
