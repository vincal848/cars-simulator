"""Tunable rule constants, loaded from ``content/common/defines.json``.

Balance numbers live in data, like a Paradox ``defines`` file, so adjusting a
modifier never means editing simulation code. Each section is a frozen
dataclass: a missing or misspelled key fails loudly at import time.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from cars.paths import load_content


@dataclass(frozen=True)
class MovementDefines:
    terrain_cost: Mapping[str, float]
    role_terrain_factor: Mapping[str, Mapping[str, float]]
    mountain_pass_factor: float
    road_discount_per_level: float
    max_road_levels: int
    edge_infrastructure_speedup: float
    river_crossing_cost: float
    zone_of_control_cost: float
    minimum_step_cost: float
    unsupplied_cost_factor: float


@dataclass(frozen=True)
class CombatDefines:
    terrain_defense: Mapping[str, float]
    river_attack_factor: float
    mountain_origin_bonus: float
    unsupplied_factor: float
    artillery_bonus_per_gun: float
    artillery_bonus_cap: float
    artillery_guns_committed: int
    minimum_defense: float
    attacker_loss_ratio: float
    attacker_minimum_loss: float
    defender_loss_ratio: float
    defender_minimum_loss: float


@dataclass(frozen=True)
class NavalDefines:
    attacker_loss_ratio: float
    defender_loss_ratio: float
    minimum_loss: float


@dataclass(frozen=True)
class AirDefines:
    strike_factor: float
    minimum_strike: float
    return_fire_ratio: float
    interceptor_factor: float
    support_bonus: float


@dataclass(frozen=True)
class RecruitmentDefines:
    regional_surcharge: int


@dataclass(frozen=True)
class RecoveryDefines:
    per_turn: float
    city_bonus: float


@dataclass(frozen=True)
class UpkeepDefines:
    per_unit: Mapping[str, Mapping[str, float]]
    shortfall_attrition: float


@dataclass(frozen=True)
class JournalDefines:
    entry_limit: int


@dataclass(frozen=True)
class AIDefines:
    attack_margin: float
    hostile_province_score: float
    front_distance_weight: float
    unknown_front_distance: int
    route_cost_weight: float
    rejected_score: float
    recruitment_rotation: tuple[str, ...]


@dataclass(frozen=True)
class Defines:
    movement: MovementDefines
    combat: CombatDefines
    naval: NavalDefines
    air: AirDefines
    recruitment: RecruitmentDefines
    recovery: RecoveryDefines
    upkeep: UpkeepDefines
    journal: JournalDefines
    ai: AIDefines

    @classmethod
    def load(cls) -> "Defines":
        raw = load_content("common", "defines.json")
        ai = dict(raw["ai"], recruitment_rotation=tuple(raw["ai"]["recruitment_rotation"]))
        return cls(
            movement=MovementDefines(**raw["movement"]),
            combat=CombatDefines(**raw["combat"]),
            naval=NavalDefines(**raw["naval"]),
            air=AirDefines(**raw["air"]),
            recruitment=RecruitmentDefines(**raw["recruitment"]),
            recovery=RecoveryDefines(**raw["recovery"]),
            upkeep=UpkeepDefines(**raw["upkeep"]),
            journal=JournalDefines(**raw["journal"]),
            ai=AIDefines(**ai),
        )


DEFINES = Defines.load()
