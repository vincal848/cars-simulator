"""Fleets move between sea zones and fight enemy fleets on entry."""

from typing import TYPE_CHECKING

from cars.sim.defines import DEFINES
from cars.sim.entities import FLEET
from cars.sim.graph import Paths, step_cost
from cars.sim.journal import NAVAL_BATTLE, battle_report, snapshot

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.state import GameState

RULES = DEFINES.naval


def enemy_fleets(state: "GameState", unit: "Unit", sea: str) -> list["Unit"]:
    return state.enemy_units_at(sea, unit.owner, {FLEET})


def reachable_seas(state: "GameState", unit: "Unit") -> Paths:
    """Sea zones within range; zones held by an enemy fleet end the route."""
    return state.naval.shortest_paths(
        unit.location,
        step_cost,
        unit.remaining,
        lambda sea: not enemy_fleets(state, unit, sea),
    )


def resolve_naval(state: "GameState", attacker: "Unit", sea: str) -> tuple[bool, str]:
    """Engage every enemy fleet in ``sea``; success means the zone is cleared."""
    before = snapshot(state)
    defenders = enemy_fleets(state, attacker, sea)
    if not defenders:
        return True, "Sea zone clear."
    strength = attacker.attack_power()
    defense = sum(unit.defense_power() for unit in defenders)
    attacker.hp -= max(RULES.minimum_loss, defense * RULES.attacker_loss_ratio)
    for unit in defenders:
        unit.hp -= max(RULES.minimum_loss, strength * RULES.defender_loss_ratio / len(defenders))
        if unit.hp <= 0:
            del state.units[unit.id]
    if attacker.hp <= 0:
        del state.units[attacker.id]

    survived = attacker.id in state.units
    success = survived and not enemy_fleets(state, attacker, sea)
    if success:
        message = "Enemy fleet cleared."
    elif not survived:
        message = "Fleet lost."
    else:
        message = "Naval engagement; enemy still holds the sea."
    battle_report(state, before, NAVAL_BATTLE, message, sea, f"Attack {strength:.1f} / defense {defense:.1f}")
    return success, message
