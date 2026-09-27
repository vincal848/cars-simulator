"""Fog of war: what a faction can currently see.

A faction sees its own provinces and their neighbours, everything next to its
units, the sea zones beside its ports and fleets, and what its balloons observe.
The map itself is always known; only enemy forces are hidden.
"""

from typing import TYPE_CHECKING

from cars.sim.balloons import observed
from cars.sim.entities import FLEET

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.state import GameState


def visible_nodes(state: "GameState", owner: str) -> set[str]:
    seen: set[str] = set()
    for province in state.provinces.values():
        if province.controller != owner:
            continue
        seen.add(province.id)
        seen.update(neighbor for neighbor, _ in state.land.neighbors(province.id))
        port = state.ports.get(province.id)
        if port:
            seen.add(port)
    for unit in state.units.values():
        if unit.owner != owner:
            continue
        seen.add(unit.location)
        graph = state.naval if unit.kind == FLEET else state.land
        seen.update(neighbor for neighbor, _ in graph.neighbors(unit.location))
    seen.update(observed(state, owner))
    return seen


def can_see(unit: "Unit", viewer: str | None, visible: set[str] | None) -> bool:
    """Whether ``viewer`` can see ``unit``; ``visible`` of None means no fog."""
    return visible is None or unit.owner == viewer or unit.location in visible
