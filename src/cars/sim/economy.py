"""Resource production, collected at the end of each faction's turn."""

from typing import TYPE_CHECKING

from cars.sim.buildings import BUILDINGS
from cars.sim.entities import RESOURCES

if TYPE_CHECKING:
    from cars.sim.state import GameState


def forecast(state: "GameState", owner: str) -> dict[str, float]:
    """Expected income. Regional output is shared by controlled-province share;
    resource sites and buildings are local."""
    gains = dict.fromkeys(RESOURCES, 0.0)
    for region in state.regions.values():
        held = [state.provinces[p] for p in region.provinces if state.provinces[p].controller == owner]
        for resource in RESOURCES:
            gains[resource] += region.production[resource] * len(held) / len(region.provinces)
            gains[resource] += sum(p.resource_sites.get(resource, 0) for p in held)
    for province in state.provinces.values():
        if province.controller != owner:
            continue
        for kind, level in province.buildings.items():
            spec = BUILDINGS[kind]
            if spec.produces:
                gains[spec.resource] += level * spec.output
    return gains


def produce(state: "GameState", owner: str) -> dict[str, float]:
    gains = forecast(state, owner)
    stock = state.factions[owner].resources
    for resource, amount in gains.items():
        stock[resource] += amount
    return gains
