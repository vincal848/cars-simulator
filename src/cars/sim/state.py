"""The complete, serializable game state."""

from dataclasses import dataclass, field

from cars.sim.calendar import new_clock
from cars.sim.entities import City, Faction, Province, Region, Unit
from cars.sim.graph import Graph
from cars.sim.market import new_stock

# Turn order, replays and the AI all assume one human and seven rival factions.
FACTION_COUNT = 8


@dataclass
class GameState:
    provinces: dict[str, Province]
    regions: dict[str, Region]
    cities: dict[str, City]
    factions: dict[str, Faction]
    units: dict[str, Unit]
    land: Graph
    naval: Graph
    air: Graph
    supply: Graph
    ports: dict[str, str]
    active_index: int = 0
    round: int = 1
    objectives: dict = field(default_factory=dict)
    recruited: list[str] = field(default_factory=list)
    market: dict[str, int] = field(default_factory=new_stock)
    tutorial: dict = field(default_factory=dict)
    clock: dict = field(default_factory=new_clock)
    reports: list[dict] = field(default_factory=list)
    air_support: list[dict] = field(default_factory=list)

    @property
    def active(self) -> str:
        """ID of the faction whose turn it is."""
        return list(self.factions)[self.active_index]

    @property
    def player(self) -> str | None:
        """The human faction, once a campaign has been chosen."""
        return self.objectives.get("player")

    def graph(self, layer: str) -> Graph:
        return {"land": self.land, "naval": self.naval, "air": self.air, "supply": self.supply}[layer]

    def controls(self, owner: str, province: str) -> bool:
        return province in self.provinces and self.provinces[province].controller == owner

    def cities_in(self, province: str) -> list[City]:
        return [city for city in self.cities.values() if city.province == province]

    def has_city(self, province: str) -> bool:
        return any(city.province == province for city in self.cities.values())

    def enemy_units_at(self, location: str, owner: str, kinds: frozenset[str] | set[str]) -> list[Unit]:
        return [
            unit
            for unit in self.units.values()
            if unit.location == location and unit.owner != owner and unit.kind in kinds
        ]

    def reindex_units(self) -> None:
        """Rebuild each province's list of stationed land units."""
        for province in self.provinces.values():
            province.units.clear()
        for unit in self.units.values():
            if unit.is_land:
                self.provinces[unit.location].units.append(unit.id)
