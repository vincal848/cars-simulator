"""Air groups fly one sortie per turn from a controlled airbase: strike, support or rebase.

Operational range is distance on a dedicated air graph, so the metric can be
replaced without changing the interface.
"""

from typing import TYPE_CHECKING

from cars.sim.defines import DEFINES
from cars.sim.entities import AIR, FLEET, FULL_STRENGTH, LAND_KINDS
from cars.sim.graph import step_cost
from cars.sim.journal import AIR_STRIKE, battle_report, record, snapshot
from cars.sim.objectives import evaluate
from cars.sim.supply import refresh_supply

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.state import GameState

RULES = DEFINES.air
STRIKE, SUPPORT, REBASE = "strike", "support", "rebase"
MISSIONS = (STRIKE, SUPPORT, REBASE)
STRIKE_TARGET_KINDS = LAND_KINDS | {FLEET}


def is_airbase(state: "GameState", owner: str, province: str) -> bool:
    """A controlled province with an airfield or an airbase city."""
    if not state.controls(owner, province):
        return False
    if state.provinces[province].buildings.get("airfield", 0) > 0:
        return True
    return any(city.province == province and city.airbase for city in state.cities.values())


def coverage(state: "GameState", unit: "Unit") -> set[str]:
    """Nodes within range of ``unit``; empty when its base has been lost."""
    if not is_airbase(state, unit.owner, unit.location):
        return set()
    return set(state.air.shortest_paths(unit.location, step_cost, unit.allowance).costs)


def support_bonus_at(state: "GameState", owner: str, target: str) -> float:
    """Attack bonus from close air support ordered over ``target``. Does not stack."""
    for order in state.air_support:
        if order["owner"] != owner or order["target"] != target:
            continue
        unit = state.units.get(order["unit"])
        if unit is not None and is_airbase(state, owner, unit.location):
            return RULES.support_bonus
    return 0.0


def mission(state: "GameState", unit_id: str, target: str, kind: str = STRIKE) -> tuple[bool, str]:
    unit = state.units.get(unit_id)
    if not unit or unit.kind != AIR or unit.owner != state.active:
        return False, "Select your own air group."
    if unit.remaining <= 0:
        return False, "This air group has no sortie remaining this turn."
    if kind not in MISSIONS or target not in coverage(state, unit):
        return False, "Target is outside operational range or the base is lost."
    if kind == REBASE:
        return _rebase(state, unit, target)
    if kind == SUPPORT:
        return _assign_support(state, unit, target)
    return _strike(state, unit, target)


def _cancel_support(state: "GameState", unit_id: str) -> None:
    state.air_support = [order for order in state.air_support if order["unit"] != unit_id]


def _rebase(state: "GameState", unit: "Unit", target: str) -> tuple[bool, str]:
    if target == unit.location or not is_airbase(state, unit.owner, target):
        return False, "Choose another controlled airbase within range."
    unit.location = target
    unit.remaining = 0
    _cancel_support(state, unit.id)
    record(state, "air mission", "Air group rebased.", target, [unit.id])
    return True, "Air group rebased; ready next turn."


def _assign_support(state: "GameState", unit: "Unit", target: str) -> tuple[bool, str]:
    if target not in state.provinces:
        return False, "Support requires a land province."
    unit.remaining = 0
    _cancel_support(state, unit.id)
    state.air_support.append(dict(unit=unit.id, owner=unit.owner, target=target))
    bonus = f"+{RULES.support_bonus:.0%} land attack here until your next turn"
    record(state, "air mission", "Close air support assigned.", target, [bonus + "; does not stack."])
    return True, f"Support assigned: {bonus}."


def _strike(state: "GameState", unit: "Unit", target: str) -> tuple[bool, str]:
    victims = state.enemy_units_at(target, unit.owner, STRIKE_TARGET_KINDS)
    if not victims:
        return False, "No enemy land forces or fleets at this target."
    before = snapshot(state)
    interceptors = [
        other
        for other in state.units.values()
        if other.kind == AIR
        and other.owner != unit.owner
        and other.remaining > 0
        and target in coverage(state, other)
    ]
    unit.remaining = 0

    damage = max(RULES.minimum_strike, unit.attack_power() * RULES.strike_factor)
    for victim in victims:
        victim.hp -= damage / len(victims)
        if victim.hp <= 0:
            del state.units[victim.id]
    return_fire = sum(v.defense * before[v.id][2] / FULL_STRENGTH for v in victims)
    retaliation = return_fire * RULES.return_fire_ratio
    for interceptor in interceptors:
        retaliation += interceptor.attack_power() * RULES.interceptor_factor
        interceptor.remaining = 0
    unit.hp -= retaliation
    if unit.hp <= 0:
        del state.units[unit.id]

    state.reindex_units()
    refresh_supply(state)
    evaluate(state)
    if unit.id in state.units:
        message = "Air strike resolved."
    else:
        message = "Air strike resolved; attacking group lost."
    factors = f"Strike {damage:.1f} / return fire {retaliation:.1f} / interceptors {len(interceptors)}"
    battle_report(state, before, AIR_STRIKE, message, target, factors)
    return True, message
