"""Loading a scenario: provinces, regions, cities, units and the four movement graphs."""

from pathlib import Path
from typing import NamedTuple

from cars.paths import content_path, load_content, read_json
from cars.sim.entities import RESOURCES, UNIT_STATS, City, Faction, Province, Region, Unit
from cars.sim.graph import Edge, Graph
from cars.sim.market import RULES as MARKET_RULES
from cars.sim.objectives import DEFAULT_RULES
from cars.sim.state import FACTION_COUNT, GameState
from cars.sim.supply import refresh_supply

DETAILED_SCENARIO = content_path("scenarios", "americas_detailed.json")
# The original 24-province layout, kept as a small, stable fixture for tests.
COMPACT_SCENARIO = content_path("scenarios", "americas.json")

LAYERS = ("land", "naval", "air", "supply")


class Scenario(NamedTuple):
    state: GameState
    shapes: dict  # province shape id -> GeoJSON geometry (+ label anchor)
    seas: list[dict]  # sea zones: id, name and map anchor


def build_graph(layer: str, nodes: list[str], edges: list[dict]) -> Graph:
    graph = Graph()
    for node in nodes:
        graph.add_node(node)
    for item in edges:
        if item["a"] not in graph or item["b"] not in graph:
            raise ValueError(f"Unknown {layer} edge endpoint")
        graph.connect(item["a"], item["b"], Edge(**item.get("metadata", {})))
    return graph


def load_scenario(path: Path = DETAILED_SCENARIO) -> Scenario:
    path = Path(path)
    raw = read_json(path)
    factions = {f["id"]: Faction(**f) for f in load_content("common", "factions.json")}
    if len(factions) != FACTION_COUNT:
        raise ValueError(f"The campaign requires exactly {FACTION_COUNT} factions")
    provinces = {p["id"]: Province(**p) for p in raw["provinces"]}
    regions = {r["id"]: Region(**r) for r in raw["regions"]}
    cities = {c["id"]: City(**c) for c in raw["cities"]}
    units = {u["id"]: Unit(**(UNIT_STATS[u["kind"]] | u)) for u in raw["units"]}
    graphs = {
        layer: build_graph(layer, raw["graphs"][layer]["nodes"], raw["graphs"][layer]["edges"])
        for layer in LAYERS
    }
    geometry = read_json(path.parent / raw["geometry"])
    shapes = {
        feature["id"]: dict(feature["geometry"], anchor=feature.get("properties", {}).get("anchor"))
        for feature in geometry["features"]
    }

    for province in provinces.values():
        known = (
            province.shape_id in shapes
            and province.region_id in regions
            and province.controller in factions
            and province.owner in factions
        )
        if not known:
            raise ValueError(f"Invalid province {province.id}")
        if province.id not in regions[province.region_id].provinces:
            raise ValueError("Region membership mismatch")
    if set(graphs["land"].adj) != set(provinces) or set(graphs["supply"].adj) != set(provinces):
        raise ValueError("Land and supply nodes must match provinces")

    for city in cities.values():
        provinces[city.province].cities.append(city.id)
    for region in regions.values():
        members = [c for c in cities.values() if c.province in region.provinces]
        region.industry = sum(c.industry for c in members)
        region.population = sum(c.population for c in members)
        region.resource_sites = {
            resource: sum(provinces[p].resource_sites.get(resource, 0) for p in region.provinces)
            for resource in RESOURCES
        }

    state = GameState(provinces, regions, cities, factions, units, **graphs, ports=raw["ports"])
    state.objectives = {"rules": dict(raw.get("objectives", DEFAULT_RULES))}
    state.reindex_units()
    for faction in factions.values():
        faction.gold = raw.get("starting_gold", MARKET_RULES.starting_gold)
        faction.resources.update(raw.get("starting_resources", {}))
    refresh_supply(state)
    return Scenario(state, shapes, raw["sea_zones"])
