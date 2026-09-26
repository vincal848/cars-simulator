"""Scripted events, defined as data in ``content/events/*.json``.

Each event has a trigger (conditions that must all hold) and two or more options,
each with effects. Triggers are checked when the player's turn begins; at most
one new event is offered per turn and each fires only once per campaign.
Choosing an option is an ordinary command, so it is saved and replayed.

Trigger and effect names map to the small functions below, so content authors
get a clear error at start-up for any name the game does not understand.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cars.paths import CONTENT_DIR, read_json
from cars.sim.entities import FLEET, FULL_STRENGTH, RESOURCES, UNIT_KINDS, UNIT_STATS, Unit
from cars.sim.journal import record
from cars.sim.market import RULES as MARKET_RULES
from cars.sim.objectives import controlled_cities
from cars.sim.state import PEACE
from cars.sim.supply import refresh_supply

if TYPE_CHECKING:
    from cars.sim.state import GameState

EVENT = "event"


@dataclass(frozen=True)
class Option:
    label: str
    effects: dict


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    text: str
    trigger: dict
    options: tuple[Option, ...]


# Triggers --------------------------------------------------------------------------


def _own_units(state: "GameState", owner: str) -> list[Unit]:
    return [u for u in state.units.values() if u.owner == owner]


def _partners(state: "GameState", owner: str) -> list[str]:
    return [
        other
        for other in state.factions
        if other != owner and state.relation(owner, other)["status"] == PEACE
    ]


TRIGGERS: dict[str, Callable[["GameState", str, object], bool]] = {
    "round_at_least": lambda state, owner, n: state.round >= n,
    "cities_at_least": lambda state, owner, n: len(controlled_cities(state, owner)) >= n,
    "cities_below": lambda state, owner, n: len(controlled_cities(state, owner)) < n,
    "units_at_least": lambda state, owner, n: len(_own_units(state, owner)) >= n,
    "damaged_units_at_least": lambda state, owner, n: (
        sum(u.hp < FULL_STRENGTH for u in _own_units(state, owner)) >= n
    ),
    "gold_at_least": lambda state, owner, n: state.factions[owner].gold >= n,
    "stock_below": lambda state, owner, stock: any(
        state.factions[owner].resources[resource] < amount for resource, amount in stock.items()
    ),
    "stock_at_least": lambda state, owner, stock: all(
        state.factions[owner].resources[resource] >= amount for resource, amount in stock.items()
    ),
    "at_peace_with_any": lambda state, owner, wanted: bool(_partners(state, owner)) == wanted,
}


# Effects ---------------------------------------------------------------------------


def _add_resources(state: "GameState", owner: str, amounts: dict) -> None:
    stock = state.factions[owner].resources
    for resource, amount in amounts.items():
        stock[resource] = max(0, stock[resource] + amount)


def _add_gold(state: "GameState", owner: str, amount: float) -> None:
    faction = state.factions[owner]
    faction.gold = max(0, faction.gold + amount)


def _heal_units(state: "GameState", owner: str, amount: float) -> None:
    for unit in _own_units(state, owner):
        unit.hp = min(FULL_STRENGTH, unit.hp + amount)


def _weaken_units(state: "GameState", owner: str, amount: float) -> None:
    """Lose strength without ever destroying a unit outright."""
    for unit in _own_units(state, owner):
        if unit.is_land:
            unit.hp = max(1, unit.hp - amount)


def _raise_unit(state: "GameState", owner: str, kind: str) -> None:
    """A free unit at the first city the faction controls (fleets in its port)."""
    for city in controlled_cities(state, owner):
        location = city.province
        if kind == FLEET:
            location = state.ports.get(city.province)
            if location not in state.naval:
                continue
        number = 1
        while f"{kind}_{owner}_event{number}" in state.units:
            number += 1
        unit_id = f"{kind}_{owner}_event{number}"
        state.units[unit_id] = Unit(unit_id, owner, location, kind, **(UNIT_STATS[kind] | {"remaining": 0}))
        state.reindex_units()
        refresh_supply(state)
        return


def _merchant_stock(state: "GameState", _owner: str, amounts: dict) -> None:
    for resource, amount in amounts.items():
        state.market[resource] = max(0, min(MARKET_RULES.capacity, state.market[resource] + amount))


EFFECTS: dict[str, Callable[["GameState", str, object], None]] = {
    "add_resources": _add_resources,
    "add_gold": _add_gold,
    "heal_units": _heal_units,
    "weaken_units": _weaken_units,
    "raise_unit": _raise_unit,
    "merchant_stock": _merchant_stock,
}


# Loading ---------------------------------------------------------------------------


def _check_resources(event_id: str, amounts: object) -> None:
    if not isinstance(amounts, dict) or not set(amounts) <= set(RESOURCES):
        raise ValueError(f"Event {event_id}: resource amounts must use {', '.join(RESOURCES)}")


def parse_event(raw: dict) -> Event:
    event_id = raw["id"]
    for name, value in raw["trigger"].items():
        if name not in TRIGGERS:
            raise ValueError(f"Event {event_id}: unknown trigger {name!r}")
        if name.startswith("stock_"):
            _check_resources(event_id, value)
    options = []
    for option in raw["options"]:
        for name, value in option["effects"].items():
            if name not in EFFECTS:
                raise ValueError(f"Event {event_id}: unknown effect {name!r}")
            if name in ("add_resources", "merchant_stock"):
                _check_resources(event_id, value)
            if name == "raise_unit" and value not in UNIT_KINDS:
                raise ValueError(f"Event {event_id}: unknown unit kind {value!r}")
        options.append(Option(option["label"], option["effects"]))
    if len(options) < 2:
        raise ValueError(f"Event {event_id}: an event needs at least two options")
    return Event(event_id, raw["title"], raw["text"], raw["trigger"], tuple(options))


def load_events() -> dict[str, Event]:
    events: dict[str, Event] = {}
    for path in sorted((CONTENT_DIR / "events").glob("*.json")):
        for raw in read_json(path):
            event = parse_event(raw)
            if event.id in events:
                raise ValueError(f"Duplicate event id {event.id!r} in {path.name}")
            events[event.id] = event
    return events


EVENTS = load_events()


# Running events --------------------------------------------------------------------


def triggered(state: "GameState", owner: str, event: Event) -> bool:
    return all(TRIGGERS[name](state, owner, value) for name, value in event.trigger.items())


def check_events(state: "GameState", owner: str) -> str | None:
    """Offer the first event whose trigger now holds; returns its id."""
    log = state.events
    for event in EVENTS.values():
        if event.id not in log["fired"] and triggered(state, owner, event):
            log["fired"].append(event.id)
            log["pending"].append(event.id)
            return event.id
    return None


def choose_option(state: "GameState", owner: str, event_id: str, index: int) -> tuple[bool, str]:
    if owner != state.active or event_id not in state.events["pending"] or event_id not in EVENTS:
        return False, "That event is not waiting for a decision."
    event = EVENTS[event_id]
    if not 0 <= index < len(event.options):
        return False, "Choose one of the offered options."
    option = event.options[index]
    for name, value in option.effects.items():
        EFFECTS[name](state, owner, value)
    state.events["pending"].remove(event_id)
    record(state, EVENT, event.title, details=[option.label], participants=[owner])
    return True, f"{event.title}: {option.label}"
