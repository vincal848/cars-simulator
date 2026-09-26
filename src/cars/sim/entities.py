"""Map entities. Field names are part of the save format and replay hashes."""

from dataclasses import dataclass, field

from cars.paths import load_content

INFANTRY = "infantry"
SCOUT = "scout"
CAVALRY = "cavalry"
ARTILLERY = "artillery"
FLEET = "fleet"
AIR = "air"

LAND_KINDS = frozenset((INFANTRY, SCOUT, CAVALRY, ARTILLERY))
UNIT_KINDS = LAND_KINDS | {FLEET, AIR}
RESOURCES = ("wood", "food", "iron")

# Hit points of a regiment at full strength; combat scales ratings by hp / FULL_STRENGTH.
FULL_STRENGTH = 10
# Movement allowance, attack and defence of each unit kind.
UNIT_STATS: dict[str, dict] = load_content("common", "units.json")


@dataclass
class Province:
    id: str
    name: str
    region_id: str
    terrain: str
    owner: str
    controller: str
    shape_id: str
    cities: list[str] = field(default_factory=list)
    units: list[str] = field(default_factory=list)
    local_modifiers: dict = field(default_factory=dict)
    resource_sites: dict = field(default_factory=dict)
    buildings: dict = field(default_factory=dict)
    geography: dict = field(default_factory=dict)


@dataclass
class Region:
    id: str
    name: str
    provinces: list[str]
    production: dict
    industry: int = 0
    population: int = 0
    resource_sites: dict = field(default_factory=dict)


@dataclass
class City:
    id: str
    name: str
    province: str
    industry: int = 2
    population: int = 100
    supply_hub: bool = True
    port: str | None = None
    airbase: bool = True
    coordinates: list | None = None
    style: str = ""
    location_source: str = "Province supply-hub anchor"


@dataclass
class Faction:
    id: str
    name: str
    color: list[int]
    style: str = "northern"
    gold: int = 100
    resources: dict = field(default_factory=lambda: dict(wood=0, food=0, iron=0))


@dataclass
class Unit:
    id: str
    owner: str
    location: str
    kind: str = INFANTRY
    allowance: float = 6
    remaining: float = 6
    attack: float = 6
    defense: float = 4
    hp: float = FULL_STRENGTH
    supplied: bool = True
    regional: str = ""

    @property
    def is_land(self) -> bool:
        return self.kind in LAND_KINDS

    @property
    def layer(self) -> str:
        """The map layer this unit is commanded from."""
        if self.kind == FLEET:
            return "naval"
        if self.kind == AIR:
            return "air"
        return "land"

    def attack_power(self) -> float:
        return self.attack * self.hp / FULL_STRENGTH

    def defense_power(self) -> float:
        return self.defense * self.hp / FULL_STRENGTH
