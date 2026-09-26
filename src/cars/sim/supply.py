"""Supply is connectivity: a land unit is supplied when a chain of provinces its
faction controls links it to a controlled supply hub."""

from collections import deque
from typing import TYPE_CHECKING

from cars.sim.entities import LAND_KINDS

if TYPE_CHECKING:
    from cars.sim.state import GameState


def supply_hubs(state: "GameState", owner: str) -> list[str]:
    return [
        city.province
        for city in state.cities.values()
        if city.supply_hub and state.provinces[city.province].controller == owner
    ]


def supplied_provinces(state: "GameState", owner: str) -> set[str]:
    return state.supply.reachable_from(
        supply_hubs(state, owner), lambda province: state.controls(owner, province)
    )


def refresh_supply(state: "GameState") -> None:
    coverage = {faction: supplied_provinces(state, faction) for faction in state.factions}
    for unit in state.units.values():
        if unit.is_land:
            unit.supplied = unit.location in coverage[unit.owner]


def supply_route(state: "GameState", owner: str, destination: str) -> list[str]:
    """Fewest supply links from a controlled hub to ``destination`` (breadth-first).

    Independent of movement costs; empty when the destination is cut off.
    """
    hubs = sorted(set(supply_hubs(state, owner)))
    parents: dict[str, str | None] = {hub: None for hub in hubs}
    pending = deque(hubs)
    while pending:
        node = pending.popleft()
        if node == destination:
            path = [node]
            while parents[path[-1]] is not None:
                path.append(parents[path[-1]])
            return path[::-1]
        for neighbor, _ in state.supply.neighbors(node):
            if neighbor not in parents and state.provinces[neighbor].controller == owner:
                parents[neighbor] = node
                pending.append(neighbor)
    return []


def threatened_route(state: "GameState", owner: str, route: list[str]) -> set[str]:
    """Provinces on ``route`` adjacent to an enemy land unit.

    A warning sign only; it does not predict that supply will be lost.
    """
    enemies = {
        u.location for u in state.units.values() if u.kind in LAND_KINDS and state.at_war(owner, u.owner)
    }
    return {p for p in route if any(n in enemies for n, _ in state.land.neighbors(p))}
