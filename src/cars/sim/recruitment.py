"""Raising new units in controlled cities. Each city recruits at most once per turn."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cars.paths import load_content
from cars.sim.defines import DEFINES
from cars.sim.entities import AIR, FLEET, UNIT_STATS, Unit
from cars.sim.journal import record
from cars.sim.regional import charter_for
from cars.sim.supply import refresh_supply

if TYPE_CHECKING:
    from cars.sim.state import GameState

REGIONAL = "regional"
RECRUITS: dict[str, dict] = load_content("common", "recruitment.json")

# Service branches need a facility in the recruiting province.
REQUIRED_FACILITY = {FLEET: "shipyard", AIR: "airfield"}


@dataclass(frozen=True)
class RecruitOption:
    """What a recruit button offers: display name, cost and the unit it creates."""

    name: str
    role: str
    cost: dict[str, int]
    base_kind: str
    stats: dict = field(repr=False)
    charter: str = ""


def recruit_option(state: "GameState", province: str, kind: str) -> RecruitOption | None:
    if kind == REGIONAL:
        charter = charter_for(state, province)
        if charter is None:
            return None
        base = RECRUITS[charter.kind]
        surcharge = DEFINES.recruitment.regional_surcharge
        return RecruitOption(
            name=charter.name,
            role=f"Regional charter: {charter.discount:.0%} lower terrain cost in {charter.terrain}.",
            cost={resource: amount + surcharge for resource, amount in base["cost"].items()},
            base_kind=charter.kind,
            stats=UNIT_STATS[charter.kind],
            charter=charter.id,
        )
    if kind not in RECRUITS:
        return None
    spec = RECRUITS[kind]
    return RecruitOption(spec["name"], spec["role"], spec["cost"], kind, UNIT_STATS[kind])


def quote_recruit(state: "GameState", province: str, kind: str) -> tuple[dict[str, int], str]:
    """Cost of recruiting ``kind`` in ``province`` and why it is refused (empty when allowed)."""
    if province not in state.provinces or kind not in set(RECRUITS) | {REGIONAL}:
        return {}, "Choose a recruitable regiment."
    option = recruit_option(state, province, kind)
    if option is None:
        return {}, "No regional charter in this scenario."
    cost = option.cost
    if state.provinces[province].controller != state.active:
        return cost, "Requires your control."
    if not state.has_city(province):
        return cost, "Recruit at a city or supply hub."
    facility = REQUIRED_FACILITY.get(kind)
    if facility and not state.provinces[province].buildings.get(facility, 0):
        return cost, "Build a " + facility + " first."
    if kind == FLEET and state.ports.get(province) not in state.naval:
        return cost, "No connected sea zone."
    if province in state.recruited:
        return cost, "This city has recruited this turn."
    stock = state.factions[state.active].resources
    if any(stock[resource] < amount for resource, amount in cost.items()):
        return cost, "Insufficient resources."
    return cost, ""


def recruit(state: "GameState", province: str, kind: str) -> tuple[str | None, str]:
    """Recruit a unit; returns its new id, or None and the reason it was refused."""
    cost, error = quote_recruit(state, province, kind)
    if error:
        return None, error
    option = recruit_option(state, province, kind)
    number = 1
    while f"{kind}_{state.active}_{number}" in state.units:
        number += 1
    unit_id = f"{kind}_{state.active}_{number}"
    location = state.ports[province] if kind == FLEET else province
    # New units muster this turn and move from the next one.
    stats = option.stats | {"remaining": 0}
    unit = Unit(unit_id, state.active, location, option.base_kind, regional=option.charter, **stats)
    stock = state.factions[state.active].resources
    for resource, amount in cost.items():
        stock[resource] -= amount
    state.units[unit_id] = unit
    state.recruited.append(province)
    state.reindex_units()
    refresh_supply(state)
    record(state, "recruitment", option.name + " recruited.", province, [unit_id])
    if kind == AIR:
        return unit_id, option.name + " formed. Select Air to see coverage."
    return unit_id, option.name + " recruited. Ready to move next turn."
