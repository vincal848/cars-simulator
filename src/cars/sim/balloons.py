"""Balloon corps: tethered observation balloons that go up once per turn.

An ascent over a province within range reveals it and its neighbours until the
corps' next turn, and lets friendly batteries attacking it fire on observed
targets. A corps can instead relocate to another province its nation controls.
Range is distance on the dedicated air graph, measured from the corps' post.
"""

from typing import TYPE_CHECKING

from cars.sim.defines import DEFINES
from cars.sim.entities import BALLOON
from cars.sim.graph import step_cost
from cars.sim.journal import record

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.state import GameState

RULES = DEFINES.balloons
OBSERVE, RELOCATE = "observe", "relocate"
MISSIONS = (OBSERVE, RELOCATE)


def is_station(state: "GameState", owner: str, province: str) -> bool:
    """A controlled city, where a corps can refill its gas and mend its envelope."""
    return state.controls(owner, province) and state.has_city(province)


def coverage(state: "GameState", unit: "Unit") -> set[str]:
    """Provinces within range of ``unit``; empty while its post is in enemy hands."""
    if not state.controls(unit.owner, unit.location):
        return set()
    reachable = state.air.shortest_paths(unit.location, step_cost, unit.allowance).costs
    return {node for node in reachable if node in state.provinces}


def observed(state: "GameState", owner: str) -> set[str]:
    """Provinces ``owner``'s balloons have in view, with their neighbours."""
    seen: set[str] = set()
    for ascent in state.ascents:
        if ascent["owner"] == owner:
            seen.add(ascent["target"])
            seen.update(neighbor for neighbor, _ in state.land.neighbors(ascent["target"]))
    return seen


def spotting_at(state: "GameState", owner: str, target: str) -> float:
    """Extra effect of ``owner``'s artillery on ``target`` from an observer aloft. Does not stack."""
    for ascent in state.ascents:
        if ascent["owner"] == owner and ascent["target"] == target and ascent["unit"] in state.units:
            return RULES.spotting_bonus
    return 0.0


def mission(state: "GameState", unit_id: str, target: str, kind: str = OBSERVE) -> tuple[bool, str]:
    unit = state.units.get(unit_id)
    if not unit or unit.kind != BALLOON or unit.owner != state.active:
        return False, "Select your own balloon corps."
    if unit.remaining <= 0:
        return False, "This balloon corps has already gone up this turn."
    if kind not in MISSIONS or target not in coverage(state, unit):
        return False, "Target is out of range, or the corps' post has been lost."
    if kind == RELOCATE:
        return _relocate(state, unit, target)
    return _observe(state, unit, target)


def _cancel(state: "GameState", unit_id: str) -> None:
    state.ascents = [ascent for ascent in state.ascents if ascent["unit"] != unit_id]


def _relocate(state: "GameState", unit: "Unit", target: str) -> tuple[bool, str]:
    if target == unit.location or not state.controls(unit.owner, target):
        return False, "Choose another province you control within range."
    unit.location = target
    unit.remaining = 0
    _cancel(state, unit.id)
    state.reindex_units()
    record(state, "ascent", "Balloon corps relocated.", target, [unit.id])
    return True, "Balloon corps relocated; it can go up next turn."


def _observe(state: "GameState", unit: "Unit", target: str) -> tuple[bool, str]:
    unit.remaining = 0
    _cancel(state, unit.id)
    state.ascents.append(dict(unit=unit.id, owner=unit.owner, target=target))
    bonus = f"artillery +{RULES.spotting_bonus:.0%} against it until your next turn"
    record(state, "ascent", "Balloon ascent: province under observation.", target, [bonus])
    return True, f"Province under observation; {bonus}."
