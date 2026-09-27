"""The eight nations' histories and national traits.

Traits are data: each names a modifier the rules look up with :func:`modifier`,
so a mod can rebalance or replace them in ``content/common/nations.json``.

Modifier keys and where they apply:

- ``recruit_cost`` {unit kind: factor}: recruitment prices
- ``attack`` {unit kind: factor}: attacking strength in land battles
- ``defense_terrain`` {terrain: factor}: defending strength in that terrain
- ``defense_home`` factor: defending strength in the nation's own provinces
- ``movement_terrain`` {terrain: factor}: land movement cost into that terrain
- ``production`` {resource: factor}: income
- ``upkeep`` {resource: factor}: unit upkeep
- ``gold_income`` amount: extra gold each turn
- ``storage`` amount: extra stockpile capacity
"""

from dataclasses import dataclass

from cars.paths import load_content

KEYS = {
    "recruit_cost",
    "attack",
    "defense_terrain",
    "defense_home",
    "movement_terrain",
    "production",
    "upkeep",
    "gold_income",
    "storage",
}


@dataclass(frozen=True)
class Trait:
    name: str
    effect: str
    modifiers: dict


@dataclass(frozen=True)
class Nation:
    id: str
    capital: str
    ruler: str
    government: str
    founded: int
    motto: str
    summary: str
    history: tuple[str, ...]
    traits: tuple[Trait, ...]


def _load() -> dict[str, Nation]:
    nations = {}
    for nation_id, data in load_content("common", "nations.json").items():
        traits = tuple(Trait(**trait) for trait in data["traits"])
        for trait in traits:
            unknown = set(trait.modifiers) - KEYS
            if unknown:
                raise ValueError(f"Unknown modifier {sorted(unknown)} in trait {trait.name!r} of {nation_id}")
        nations[nation_id] = Nation(
            id=nation_id,
            **{key: data[key] for key in ("capital", "ruler", "government", "founded", "motto", "summary")},
            history=tuple(data["history"]),
            traits=traits,
        )
    return nations


NATIONS: dict[str, Nation] = _load()


def modifier(faction: str, key: str, subject: str | None = None, default: float = 1.0) -> float:
    """The combined value of modifier ``key`` for ``faction``: factors multiply, amounts add.

    ``subject`` picks the entry of a keyed modifier, such as a unit kind or resource.
    """
    nation = NATIONS.get(faction)
    if nation is None:
        return default
    value = default
    for trait in nation.traits:
        entry = trait.modifiers.get(key)
        if entry is None:
            continue
        if subject is not None:
            entry = entry.get(subject) if isinstance(entry, dict) else None
            if entry is None:
                continue
        value = value + entry if key in ("gold_income", "storage") else value * entry
    return value
