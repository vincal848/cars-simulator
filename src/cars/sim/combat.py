"""Deterministic land combat by attrition.

Both sides always take losses. An attack that fails still spends the attacker's
movement; a successful one changes the province's controller, never its owner.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cars.sim.balloons import spotting_at
from cars.sim.defines import DEFINES
from cars.sim.entities import ARTILLERY, BALLOON, LAND_KINDS
from cars.sim.journal import LAND_BATTLE, Factors, battle_report, snapshot
from cars.sim.nations import modifier

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Edge
    from cars.sim.state import GameState

RULES = DEFINES.combat


def supply_factor(unit: "Unit") -> float:
    return 1 if unit.supplied else RULES.unsupplied_factor


def resolve(
    state: "GameState", attacker: "Unit", origin: str, destination: str, edge: "Edge"
) -> tuple[bool, str]:
    """Fight for ``destination``; the modifiers go into the battle report."""
    before = snapshot(state)
    previous_controller = state.provinces[destination].controller
    success, outcome, factors = _fight(state, attacker, origin, destination, edge)
    report = battle_report(state, before, LAND_BATTLE, outcome, destination, factors)
    if previous_controller not in report["participants"]:
        report["participants"].append(previous_controller)
    return success, outcome


@dataclass(frozen=True)
class Assessment:
    """Everything that decides a land battle, computed before anyone takes losses."""

    strength: float
    defense: float
    guns: tuple["Unit", ...]
    factors: Factors

    def attacker_loss(self) -> float:
        return max(RULES.attacker_minimum_loss, self.defense * RULES.attacker_loss_ratio)

    def defender_loss(self, defenders: int) -> float:
        return max(RULES.defender_minimum_loss, self.strength * RULES.defender_loss_ratio / defenders)

    def captures(self, attacker: "Unit", defenders: list["Unit"]) -> bool:
        """Whether the attack would take the province: the attacker survives and no defender does."""
        if attacker.hp - self.attacker_loss() <= 0:
            return False
        return not defenders or all(unit.hp - self.defender_loss(len(defenders)) <= 0 for unit in defenders)


def assess(
    state: "GameState",
    attacker: "Unit",
    origin: str,
    destination: str,
    edge: "Edge",
    defenders: list["Unit"],
) -> Assessment:
    """Strength of an attack on ``destination`` against ``defenders``, without changing the state."""
    province = state.provinces[destination]
    terrain = RULES.terrain_defense[province.terrain]
    crossing = RULES.river_attack_factor if edge.river_crossing else 1
    high_ground = state.provinces[origin].terrain == "mountains"
    origin_bonus = RULES.mountain_origin_bonus if high_ground else 1
    strength = attacker.attack_power() * crossing * origin_bonus
    trait = modifier(attacker.owner, "attack", attacker.kind)
    strength *= supply_factor(attacker) * trait

    guns = tuple(
        unit
        for unit in state.units.values()
        if unit.kind == ARTILLERY
        and unit.id != attacker.id
        and unit.owner == attacker.owner
        and unit.location == origin
        and unit.remaining > 0
        and unit.supplied
    )
    artillery_bonus = min(RULES.artillery_bonus_cap, len(guns) * RULES.artillery_bonus_per_gun)
    spotting = spotting_at(state, attacker.owner, destination)
    artillery_bonus *= 1 + spotting
    strength *= 1 + artillery_bonus

    defense = sum(
        unit.defense_power() * supply_factor(unit) * _defence_traits(unit.owner, province)
        for unit in defenders
    )
    defense = max(RULES.minimum_defense, defense) * terrain
    factors = (
        ("Defender's terrain", f"×{terrain:g}"),
        ("River crossing", f"×{crossing:g}"),
        ("Attacking from high ground", f"×{origin_bonus:g}"),
        ("Attacker's supply", f"×{supply_factor(attacker):g}"),
        ("Attacker's national traits", f"×{trait:g}"),
        ("Artillery support", f"+{artillery_bonus:.0%}"),
        ("Balloon spotting for the guns", f"+{spotting:.0%}"),
        ("Attack strength", f"{strength:.1f}"),
        ("Defence strength", f"{defense:.1f}"),
    )
    return Assessment(strength, defense, guns, factors)


def _defence_traits(owner: str, province) -> float:
    """National traits that strengthen ``owner``'s defenders in ``province``."""
    factor = modifier(owner, "defense_terrain", province.terrain)
    if province.owner == owner:
        factor *= modifier(owner, "defense_home")
    return factor


def _fight(
    state: "GameState", attacker: "Unit", origin: str, destination: str, edge: "Edge"
) -> tuple[bool, str, str]:
    province = state.provinces[destination]
    defenders = state.enemy_units_at(destination, attacker.owner, LAND_KINDS)
    odds = assess(state, attacker, origin, destination, edge, defenders)
    for gun in odds.guns[: RULES.artillery_guns_committed]:
        gun.remaining = 0

    attacker.hp -= odds.attacker_loss()
    for defender in defenders:
        defender.hp -= odds.defender_loss(len(defenders))
        if defender.hp <= 0:
            del state.units[defender.id]
    if attacker.hp <= 0:
        del state.units[attacker.id]
        return False, "Attacking regiment destroyed.", odds.factors
    if any(unit.id in state.units for unit in defenders):
        return False, "Attack repulsed; defenders suffered attrition.", odds.factors

    province.controller = attacker.owner
    # Enemy balloon corps at the post are captured with their equipment.
    for unit_id, unit in list(state.units.items()):
        if unit.kind == BALLOON and unit.location == destination and unit.owner != attacker.owner:
            del state.units[unit_id]
    return True, "Province captured; ownership unchanged.", odds.factors
