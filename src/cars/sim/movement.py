"""Land movement costs and reachability.

A step's cost combines terrain, the unit's role and regional charter, roads, river
crossings and enemy zones of control, all evaluated at query time. Hostile
provinces can be entered but not passed through.
"""

from math import inf
from typing import TYPE_CHECKING

from cars.sim.defines import DEFINES
from cars.sim.graph import Edge, Paths
from cars.sim.regional import CHARTERS

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.state import GameState

RULES = DEFINES.movement


def hostile_zoc(state: "GameState", owner: str) -> set[str]:
    """Provinces next to an enemy land unit; entering one costs extra movement."""
    return {
        neighbor
        for unit in state.units.values()
        if unit.owner != owner and unit.is_land
        for neighbor, _ in state.land.neighbors(unit.location)
    }


def movement_cost(
    origin: str,
    destination: str,
    edge: Edge,
    unit: "Unit",
    state: "GameState",
    zoc: set[str] | None = None,
) -> float:
    if edge.border_type == "closed":
        return inf
    province = state.provinces[destination]
    terrain = province.terrain
    factor = RULES.terrain_cost[terrain]
    charter = CHARTERS.get(unit.regional)
    if charter and charter.terrain == terrain:
        factor *= 1 - charter.discount
    role_factors = RULES.role_terrain_factor.get(unit.kind)
    if role_factors:
        factor *= role_factors[terrain]
    if edge.mountain_pass and terrain == "mountains":
        factor *= RULES.mountain_pass_factor
    roads = min(RULES.max_road_levels, max(0, province.buildings.get("roads", 0)))
    factor *= 1 - RULES.road_discount_per_level * roads

    cost = edge.base_cost * factor / (1 + RULES.edge_infrastructure_speedup * edge.infrastructure)
    if edge.river_crossing:
        cost += RULES.river_crossing_cost
    cost += province.local_modifiers.get("movement_penalty", 0)
    if destination in (hostile_zoc(state, unit.owner) if zoc is None else zoc):
        cost += RULES.zone_of_control_cost
    cost = max(RULES.minimum_step_cost, cost)
    if not unit.supplied:
        cost *= RULES.unsupplied_cost_factor
    return cost


def reachable(state: "GameState", unit: "Unit") -> Paths:
    """Every province ``unit`` can reach with its remaining movement this turn."""
    zoc = hostile_zoc(state, unit.owner)
    return state.land.shortest_paths(
        unit.location,
        lambda a, b, edge: movement_cost(a, b, edge, unit, state, zoc),
        unit.remaining,
        lambda province: state.provinces[province].controller == unit.owner,
    )
