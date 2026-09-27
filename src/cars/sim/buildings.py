"""Province construction. Buildings stay with the province when it changes hands."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cars.paths import load_content
from cars.sim.journal import record

if TYPE_CHECKING:
    from cars.sim.state import GameState

INFRASTRUCTURE = "infrastructure"
DEFAULT_MAX_LEVEL = 3


@dataclass(frozen=True)
class BuildingSpec:
    id: str
    name: str
    cost: dict[str, int]
    resource: str | None = None
    output: int = 0
    group: str = "estate"
    max_level: int = DEFAULT_MAX_LEVEL
    description: str = ""
    effect: str = ""

    @property
    def is_infrastructure(self) -> bool:
        return self.group == INFRASTRUCTURE

    @property
    def produces(self) -> bool:
        return self.resource is not None

    def cost_at(self, level: int) -> dict[str, int]:
        """Cost of raising the building from ``level`` to ``level + 1``."""
        return {resource: amount * (level + 1) for resource, amount in self.cost.items()}

    def summary(self) -> str:
        """Short effect label shown on the build button."""
        return self.effect or f"+{self.output} {self.resource}/turn"


BUILDINGS: dict[str, BuildingSpec] = {
    key: BuildingSpec(id=key, **spec) for key, spec in load_content("common", "buildings.json").items()
}


def quote(state: "GameState", province_id: str, kind: str) -> tuple[dict[str, int], str]:
    """Cost of the next level and the reason it cannot be built (empty when allowed)."""
    if province_id not in state.provinces or kind not in BUILDINGS:
        return {}, "Select a province."
    spec = BUILDINGS[kind]
    province = state.provinces[province_id]
    level = province.buildings.get(kind, 0)
    cost = spec.cost_at(level)
    if province.controller != state.active:
        return cost, "Requires your control."
    if kind in ("shipyard", "gasworks") and not state.has_city(province_id):
        return cost, "Requires a city or supply hub."
    if kind == "shipyard" and state.ports.get(province_id) not in state.naval:
        return cost, "Requires an existing port connection."
    if level >= spec.max_level:
        return cost, "Maximum level reached."
    stock = state.factions[state.active].resources
    if any(stock[resource] < amount for resource, amount in cost.items()):
        return cost, "Insufficient resources."
    return cost, ""


def build(state: "GameState", province_id: str, kind: str) -> tuple[bool, str]:
    cost, error = quote(state, province_id, kind)
    if error:
        return False, error
    stock = state.factions[state.active].resources
    for resource, amount in cost.items():
        stock[resource] -= amount
    province = state.provinces[province_id]
    province.buildings[kind] = province.buildings.get(kind, 0) + 1
    level = province.buildings[kind]
    spec = BUILDINGS[kind]
    record(state, "construction", spec.name + " completed.", province_id, [f"Level {level}"])
    if spec.description:
        return True, f"{spec.name} completed. {spec.description}"
    return True, f"{spec.name} level {level} completed. +{spec.output} {spec.resource} per faction turn."
