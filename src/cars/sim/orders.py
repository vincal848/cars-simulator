"""Move orders for land units and fleets. Entering hostile ground or waters starts a battle."""

from typing import TYPE_CHECKING

from cars.sim.combat import resolve
from cars.sim.entities import AIR, FLEET
from cars.sim.journal import record
from cars.sim.movement import movement_cost, reachable
from cars.sim.naval import enemy_fleets, reachable_seas, resolve_naval
from cars.sim.objectives import evaluate
from cars.sim.supply import refresh_supply

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.state import GameState

# Tolerance for accumulated floating-point movement costs.
_EPSILON = 1e-9


def issue_move(state: "GameState", unit_id: str, destination: str) -> tuple[list[str], str]:
    """Move a unit along its cheapest route; returns the provinces or seas it passed through.

    A fleet ordered to its own sea zone attacks any enemy fleet sharing it.
    """
    unit = state.units.get(unit_id)
    if unit is None or unit.owner != state.active or unit.kind == AIR:
        return [], "Select an active faction unit."
    engage_here = unit.kind == FLEET and destination == unit.location and unit.remaining > 0
    if engage_here and enemy_fleets(state, unit, destination):
        unit.remaining = 0
        _, message = resolve_naval(state, unit, destination)
        return [destination], message
    paths = reachable(state, unit) if unit.is_land else reachable_seas(state, unit)
    route = paths.path(destination)
    if len(route) < 2:
        return [], "Destination is not reachable."

    traveled, message = _advance(state, unit, route)
    evaluate(state)
    state.reindex_units()
    refresh_supply(state)
    if len(traveled) > 1:
        record(
            state,
            "movement",
            unit.kind.title() + " moved.",
            traveled[-1],
            [unit.id, " -> ".join(traveled)],
        )
    return traveled, message


def _advance(state: "GameState", unit: "Unit", route: list[str]) -> tuple[list[str], str]:
    """Walk ``route`` step by step until movement runs out or a battle ends the march."""
    traveled = [unit.location]
    message = "Movement completed."
    graph = state.land if unit.is_land else state.naval
    for target in route[1:]:
        origin = unit.location
        edge = graph.edge(origin, target)
        cost = movement_cost(origin, target, edge, unit, state) if unit.is_land else edge.base_cost
        if cost > unit.remaining + _EPSILON:
            break
        unit.remaining = max(0, unit.remaining - cost)
        if unit.is_land:
            hostile = state.provinces[target].controller != unit.owner
        else:
            hostile = bool(enemy_fleets(state, unit, target))
        if hostile:
            if unit.is_land:
                won, message = resolve(state, unit, origin, target, edge)
            else:
                won, message = resolve_naval(state, unit, target)
            unit.remaining = 0
            if not won:
                break
        unit.location = target
        traveled.append(target)
        refresh_supply(state)
        if hostile:
            break
    return traveled, message
