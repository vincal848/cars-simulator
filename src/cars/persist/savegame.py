"""Versioned JSON save files.

A save is a complete snapshot, including map geometry, so it can be opened
without the scenario it came from. Loading validates every reference before
the state is used; a malformed file raises ``ValueError``.
"""

import json
import math
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from cars.paths import read_json, saves_dir, write_text_atomic
from cars.sim.calendar import date_label, validate_clock
from cars.sim.defines import DEFINES
from cars.sim.entities import AIR, FLEET, UNIT_KINDS, City, Faction, Province, Region, Unit
from cars.sim.graph import Edge, Graph
from cars.sim.market import RULES as MARKET_RULES
from cars.sim.objectives import ACTIVE, DEFEAT, VICTORY, begin
from cars.sim.regional import CHARTERS
from cars.sim.scenario import LAYERS
from cars.sim.state import FACTION_COUNT, GameState
from cars.sim.supply import refresh_supply

SAVE_VERSION = 1
# UPGRADES[n] converts a version-n save into version n + 1. When the format changes,
# bump SAVE_VERSION and register a step here instead of breaking players' saves.
UPGRADES: dict[int, Callable[[dict], dict]] = {}
ENTITY_TYPES = {
    "provinces": Province,
    "regions": Region,
    "cities": City,
    "factions": Faction,
    "units": Unit,
}
TUTORIAL_STEPS = 10

# (state, shapes, seas, player): everything needed to resume a campaign.
Loaded = tuple[GameState, dict, list, str]


class SaveLibrary:
    """Three manual campaign slots and one end-of-turn autosave."""

    SLOT_COUNT = 4
    AUTOSAVE = 3
    _FILENAMES = ("campaign.json", "slot2.json", "slot3.json", "autosave.json")

    def __init__(self, directory: Path | None = None) -> None:
        self._directory = directory

    @property
    def directory(self) -> Path:
        return self._directory or saves_dir()

    def path(self, slot: int) -> Path:
        if slot not in range(self.SLOT_COUNT):
            raise ValueError("Unknown save slot.")
        return self.directory / self._FILENAMES[slot]

    def has_save(self) -> bool:
        return any(self.path(slot).exists() for slot in range(self.SLOT_COUNT))

    def describe(self, slot: int) -> str:
        """One-line summary for the save library, e.g. "Northern Union / Summer 1801"."""
        path = self.path(slot)
        if not path.exists():
            return "Empty slot"
        try:
            data = upgrade(read_json(path))
            faction = next(f["name"] for f in data["factions"] if f["id"] == data["player"])
            validate_clock(data["clock"])
            return f"{faction} / {date_label(data['clock'])}"
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            return "Unreadable save (choose another slot)"


def encode_game(state: GameState, shapes: dict, seas: list, player: str) -> dict:
    if player not in state.factions or state.active != player:
        raise ValueError("Save during your own turn.")
    data = dict(
        version=SAVE_VERSION,
        player=player,
        round=state.round,
        active_index=state.active_index,
        shapes=shapes,
        seas=seas,
        ports=state.ports,
        objectives=state.objectives,
        recruited=state.recruited,
        market=state.market,
        reports=state.reports,
        air_support=state.air_support,
        clock=state.clock,
        tutorial=state.tutorial,
    )
    for name in ENTITY_TYPES:
        data[name] = [asdict(item) for item in getattr(state, name).values()]
    data["graphs"] = {
        layer: dict(
            nodes=state.graph(layer).nodes(),
            edges=[dict(a=a, b=b, metadata=asdict(edge)) for a, b, edge in state.graph(layer).edges()],
        )
        for layer in LAYERS
    }
    return data


def save_game(state: GameState, shapes: dict, seas: list, player: str, path: Path) -> None:
    data = encode_game(state, shapes, seas, player)
    write_text_atomic(Path(path), json.dumps(data, allow_nan=False))


def load_game(path: Path) -> Loaded:
    return decode_game(read_json(path))


def upgrade(data: dict) -> dict:
    """Bring save data from any earlier format up to SAVE_VERSION, one step at a time."""
    version = data.get("version") if isinstance(data, dict) else None
    if type(version) is not int or version < 1:
        raise ValueError("Unsupported save version.")
    if version > SAVE_VERSION:
        raise ValueError("This save was made by a newer version of C.A.R.S.")
    while version < SAVE_VERSION:
        data = UPGRADES[version](data)
        version += 1
        data["version"] = version
    return data


def decode_game(data: dict) -> Loaded:
    """Rebuild a campaign from save data, rejecting anything inconsistent."""
    data = upgrade(data)
    try:
        return _decode(data)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError(f"Malformed save data ({exc!r}).") from exc


def _decode(data: dict) -> Loaded:
    entities = {name: {item["id"]: cls(**item) for item in data[name]} for name, cls in ENTITY_TYPES.items()}
    graphs = {layer: _decode_graph(data["graphs"][layer]) for layer in LAYERS}
    state = GameState(
        **entities, **graphs, ports=data["ports"], active_index=data["active_index"], round=data["round"]
    )
    player = data["player"]
    state.clock = data["clock"]
    validate_clock(state.clock)
    state.market = data["market"]
    _check_economy(state)
    _check_turn(state, player)
    _check_references(state, data["shapes"])
    _check_units(state)
    _check_cities(state)
    state.tutorial = data["tutorial"]
    _check_tutorial(state.tutorial)
    state.reports = data["reports"]
    _check_journal(state)
    state.reports = state.reports[-DEFINES.journal.entry_limit :]
    state.air_support = data["air_support"]
    _check_air_support(state)
    state.recruited = data["recruited"]
    if not isinstance(state.recruited, list) or any(
        not isinstance(p, str) or p not in state.provinces for p in state.recruited
    ):
        raise ValueError("Invalid city recruitment record.")
    state.objectives = data["objectives"]
    # A snapshot taken before any faction was chosen has no objective yet.
    begin(state, player)
    _check_objectives(state.objectives, player)
    state.reindex_units()
    refresh_supply(state)
    return state, data["shapes"], data["seas"], player


def _decode_graph(data: dict) -> Graph:
    graph = Graph()
    for node in data["nodes"]:
        graph.add_node(node)
    for item in data["edges"]:
        if item["a"] not in graph or item["b"] not in graph:
            raise ValueError("Invalid graph endpoint.")
        metadata = dict(item["metadata"])
        metadata.pop("capacity", None)  # Unused field written by 0.24 and earlier.
        graph.connect(item["a"], item["b"], Edge(**metadata))
    return graph


def _is_count(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def _check_economy(state: GameState) -> None:
    market = state.market
    valid_market = (
        isinstance(market, dict)
        and set(market) == set(MARKET_RULES.base_prices)
        and all(isinstance(v, int) and 0 <= v <= MARKET_RULES.capacity for v in market.values())
    )
    if not valid_market or not all(_is_count(f.gold) for f in state.factions.values()):
        raise ValueError("Invalid market or treasury.")


def _check_turn(state: GameState, player: str) -> None:
    if len(state.factions) != FACTION_COUNT or not 0 <= state.active_index < FACTION_COUNT or state.round < 1:
        raise ValueError("Invalid campaign turn.")
    if player not in state.factions or state.active != player:
        raise ValueError("Invalid player turn.")


def _check_references(state: GameState, shapes: dict) -> None:
    if set(state.land.adj) != set(state.provinces) or set(state.supply.adj) != set(state.provinces):
        raise ValueError("Invalid province network.")
    for province in state.provinces.values():
        valid = (
            province.owner in state.factions
            and province.controller in state.factions
            and province.region_id in state.regions
            and province.shape_id in shapes
        )
        if not valid:
            raise ValueError("Invalid province reference.")


def _check_units(state: GameState) -> None:
    for unit in state.units.values():
        if not isinstance(unit.regional, str) or (unit.regional and unit.regional not in CHARTERS):
            raise ValueError("Invalid regional regiment.")
        nodes = state.naval.adj if unit.kind == FLEET else state.provinces
        if unit.kind not in UNIT_KINDS or unit.location not in nodes or unit.owner not in state.factions:
            raise ValueError("Invalid unit reference.")
        if not all(_is_count(value) for value in (unit.hp, unit.remaining, unit.allowance)):
            raise ValueError("Invalid unit statistics.")


def _check_cities(state: GameState) -> None:
    for city in state.cities.values():
        if city.coordinates is not None and not _is_coordinate(city.coordinates):
            raise ValueError("Invalid city coordinates.")
        if city.province not in state.provinces:
            raise ValueError("Invalid city reference.")


def _is_coordinate(value: object) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in value):
        return False
    longitude, latitude = value
    return -180 <= longitude <= 180 and -90 <= latitude <= 90


def _check_tutorial(tutorial: object) -> None:
    if not isinstance(tutorial, dict):
        raise ValueError("Invalid tutorial progress.")
    if not tutorial:
        return
    step = tutorial.get("step")
    valid = (
        type(step) is int
        and 0 <= step <= TUTORIAL_STEPS
        and type(tutorial.get("active")) is bool
        and not (tutorial["active"] and step >= TUTORIAL_STEPS)
        and type(tutorial.get("hidden", False)) is bool
        and isinstance(tutorial.get("seen", []), list)
        and all(isinstance(flag, str) for flag in tutorial.get("seen", []))
    )
    if not valid:
        raise ValueError("Invalid tutorial progress.")


def _check_journal(state: GameState) -> None:
    def valid(entry: object) -> bool:
        return (
            isinstance(entry, dict)
            and all(isinstance(entry.get(k), str) for k in ("owner", "kind", "summary", "location"))
            and isinstance(entry.get("round"), int)
            and isinstance(entry.get("details"), list)
            and all(isinstance(line, str) for line in entry["details"])
            and isinstance(entry.get("participants"), list)
            and all(faction in state.factions for faction in entry["participants"])
        )

    if not isinstance(state.reports, list) or not all(valid(entry) for entry in state.reports):
        raise ValueError("Invalid campaign journal.")


def _check_air_support(state: GameState) -> None:
    orders = state.air_support
    well_formed = isinstance(orders, list) and all(
        isinstance(order, dict)
        and order.get("owner") in state.factions
        and order.get("target") in state.provinces
        and isinstance(order.get("unit"), str)
        for order in orders
    )
    if not well_formed:
        raise ValueError("Invalid air support orders.")
    # Orders for air groups that no longer exist simply lapse.
    state.air_support = [
        order
        for order in orders
        if order["unit"] in state.units
        and state.units[order["unit"]].kind == AIR
        and state.units[order["unit"]].owner == order["owner"]
    ]


def _check_objectives(goal: object, player: str) -> None:
    valid = (
        isinstance(goal, dict)
        and goal.get("player") == player
        and goal.get("status") in (ACTIVE, VICTORY, DEFEAT)
        and isinstance(goal.get("held"), int)
        and goal["held"] >= 0
        and all(
            isinstance(goal.get("rules", {}).get(key), int) and goal["rules"][key] >= 1
            for key in ("cities", "turns")
        )
    )
    if not valid:
        raise ValueError("Invalid campaign objectives.")
