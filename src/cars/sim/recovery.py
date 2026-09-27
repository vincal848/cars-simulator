"""Recovery: damaged units regain strength at the start of their faction's turn.

Land units recover when supplied inside their own territory (faster in a city),
fleets beside one of their own ports, and balloon corps at a city they control.
"""

from typing import TYPE_CHECKING

from cars.sim.balloons import is_station
from cars.sim.defines import DEFINES
from cars.sim.entities import BALLOON, FLEET, FULL_STRENGTH

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.state import GameState

RULES = DEFINES.recovery


def recovery_rate(state: "GameState", unit: "Unit") -> float:
    """Strength ``unit`` would regain this turn where it stands (0 if none)."""
    if unit.kind == BALLOON:
        return RULES.per_turn if is_station(state, unit.owner, unit.location) else 0
    if unit.kind == FLEET:
        home_ports = {sea for province, sea in state.ports.items() if state.controls(unit.owner, province)}
        return RULES.per_turn if unit.location in home_ports else 0
    if not unit.supplied or not state.controls(unit.owner, unit.location):
        return 0
    return RULES.per_turn + (RULES.city_bonus if state.has_city(unit.location) else 0)


def recover(state: "GameState", owner: str) -> None:
    for unit in state.units.values():
        if unit.owner == owner and unit.hp < FULL_STRENGTH:
            unit.hp = min(FULL_STRENGTH, unit.hp + recovery_rate(state, unit))
