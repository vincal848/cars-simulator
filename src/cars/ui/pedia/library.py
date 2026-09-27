"""The CARSapedia's articles: authored ones from content/text, and generated ones for every
nation, unit, regional charter, building, terrain and event.

Authored text may write rule values as placeholders, such as
``{combat.river_attack_factor}`` or ``{economy.occupied_yield:%}``, which are filled
from the rules themselves, so the library never disagrees with the game. Links
between articles are written ``[[article-id]]`` or ``[[article-id|label]]``.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from cars.paths import load_content
from cars.sim.buildings import BUILDINGS
from cars.sim.defines import DEFINES
from cars.sim.entities import BALLOON, FLEET, LAND_KINDS, UNIT_STATS
from cars.sim.events import EVENTS
from cars.sim.market import RULES as MARKET
from cars.sim.nations import NATIONS
from cars.sim.recruitment import RECRUITS, REQUIRED_FACILITY
from cars.sim.regional import CHARTERS
from cars.sim.upkeep import unit_upkeep

CATEGORIES = (
    "Getting started",
    "Warfare",
    "Economy",
    "Diplomacy",
    "The world",
    "Nations",
    "Units",
    "Regional charters",
    "Buildings",
    "Terrain",
    "Events",
    "Tools",
)
TERRAINS = ("plains", "forest", "mountains")
PLACEHOLDER = re.compile(r"\{([a-z_.]+)(?::([a-z%+]+))?\}")
LINK = re.compile(r"\[\[([a-z0-9_-]+)(?:\|([^\]]+))?\]\]")

Table = tuple[str, list[str], list[list[str]]]  # (title, column titles, rows)


@dataclass
class Article:
    id: str
    title: str
    category: str
    summary: str = ""
    body: list[str] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    facts: list[tuple[str, str]] = field(default_factory=list)
    see_also: list[str] = field(default_factory=list)
    # What to draw beside the title: ("unit", kind, charter id) or ("nation", faction id).
    plate: tuple | None = None

    def text(self) -> str:
        """Everything searchable in the article, links reduced to their labels."""
        parts = [self.title, self.category, self.summary, *self.body]
        parts += [" ".join(" ".join(row) for row in rows) for _, _, rows in self.tables]
        parts += [f"{label} {value}" for label, value in self.facts]
        return LINK.sub(lambda m: m.group(2) or m.group(1), " ".join(parts))


# Placeholders ---------------------------------------------------------------------------


def _namespaces() -> dict:
    sections = {name: getattr(DEFINES, name) for name in DEFINES.__dataclass_fields__}
    return {**sections, "market": MARKET, "buildings": BUILDINGS}


def _lookup(path: str):
    value = _namespaces()
    for part in path.split("."):
        value = value[part] if isinstance(value, Mapping) else getattr(value, part)
    return value


def fill(text: str) -> str:
    """Replace every rule placeholder with its current value."""

    def value(match: re.Match) -> str:
        number = _lookup(match.group(1))
        form = match.group(2) or ""
        if form == "%":
            return f"{number * 100:g}%"
        if form == "more%":
            return f"{(number - 1) * 100:g}%"
        if form == "less%":
            return f"{(1 - number) * 100:g}%"
        return f"{number:g}" if isinstance(number, (int, float)) else str(number)

    return PLACEHOLDER.sub(value, text)


# Generated articles -------------------------------------------------------------------


def _cost(cost: Mapping) -> str:
    return ", ".join(f"{amount} {resource}" for resource, amount in cost.items() if amount) or "free"


def _unit_articles() -> list[Article]:
    notes = load_content("text", "unit_notes.json")
    movement = DEFINES.movement
    articles = []
    for kind, spec in RECRUITS.items():
        stats = UNIT_STATS[kind]
        facts = [("Movement", f"{stats['allowance']:g} a turn")]
        if kind in LAND_KINDS:
            facts += [("Attack", f"{stats['attack']:g}"), ("Defence", f"{stats['defense']:g}")]
        facts += [("Cost", _cost(spec["cost"])), ("Upkeep", _cost(unit_upkeep(kind)) + " a turn")]
        if kind in REQUIRED_FACILITY:
            facility = REQUIRED_FACILITY[kind]
            facts.append(("Needs", f"[[building-{facility}|{BUILDINGS[facility].name}]] in the city"))
        tables = []
        if kind in LAND_KINDS:
            factors = movement.role_terrain_factor.get(kind, {})
            rows = [
                [
                    terrain.title(),
                    f"×{movement.terrain_cost[terrain]:g}",
                    f"×{factors.get(terrain, 1):g}",
                    f"×{movement.terrain_cost[terrain] * factors.get(terrain, 1):g}",
                ]
                for terrain in TERRAINS
            ]
            tables.append(("Movement cost by terrain", ["Terrain", "Terrain", "This arm", "Combined"], rows))
        link = {FLEET: "naval", BALLOON: "balloons"}.get(kind, "combat")
        articles.append(
            Article(
                id="unit-" + kind,
                title=spec["name"],
                category="Units",
                summary=spec["role"] + ".",
                body=[spec["role"] + ".", notes[kind], f"See [[{link}]] and [[recruitment]]."],
                tables=tables,
                facts=facts,
                see_also=["units", "upkeep", "stacks"],
                plate=("unit", kind, ""),
            )
        )
    return articles


def _charter_articles() -> list[Article]:
    surcharge = DEFINES.recruitment.regional_surcharge
    articles = []
    for charter in CHARTERS.values():
        base = RECRUITS[charter.kind]
        cost = {resource: amount + surcharge for resource, amount in base["cost"].items()}
        articles.append(
            Article(
                id="charter-" + charter.id,
                title=charter.name,
                category="Regional charters",
                summary=f"{base['name']} of {charter.region}, quicker in {charter.terrain}.",
                body=[
                    charter.history,
                    f"A regiment of [[unit-{charter.kind}|{base['name'].lower()}]] with "
                    f"{charter.discount:.0%} lower movement cost in "
                    f"[[terrain-{charter.terrain}|{charter.terrain}]]. "
                    f"Raise it in a city you hold in {charter.region}.",
                ],
                facts=[
                    ("Region", charter.region),
                    ("Arm", base["name"]),
                    ("Home terrain", charter.terrain.title()),
                    ("Cost", _cost(cost)),
                ],
                see_also=["charters", "unit-" + charter.kind],
                plate=("unit", charter.kind, charter.id),
            )
        )
    return articles


def _building_articles() -> list[Article]:
    articles = []
    for kind, spec in BUILDINGS.items():
        rows = [[str(level + 1), _cost(spec.cost_at(level))] for level in range(spec.max_level)]
        if spec.produces:
            effect = f"Each level adds {spec.output} {spec.resource} a turn to the province's [[production]]."
        else:
            effect = spec.description + "."
        extra = {
            "shipyard": "A port city needs one to raise [[unit-fleet|fleets]].",
            "gasworks": "A city needs one to raise [[unit-balloon|balloon corps]], and they refill there.",
            "roads": "Roads cut the terrain part of every step into the province; see [[movement]].",
        }.get(kind, "")
        articles.append(
            Article(
                id="building-" + kind,
                title=spec.name,
                category="Buildings",
                summary=spec.summary(),
                body=[effect, extra] if extra else [effect],
                tables=[("Cost of each level", ["Level", "Cost"], rows)],
                facts=[("Effect", spec.summary()), ("Levels", str(spec.max_level))],
                see_also=["construction", "buildings"],
            )
        )
    return articles


def _role_factor(kind: str, terrain: str) -> float:
    return DEFINES.movement.role_terrain_factor.get(kind, {}).get(terrain, 1)


def _terrain_articles() -> list[Article]:
    movement, combat = DEFINES.movement, DEFINES.combat
    descriptions = {
        "plains": (
            "Open grassland and farmland: the cheapest ground to cross and the hardest to hold. "
            "Cavalry is at its best here."
        ),
        "forest": (
            "Woodland slows every army but cavalry most, and gives defenders cover. "
            "Scouts move through it quickly."
        ),
        "mountains": (
            "The most expensive ground to cross and the strongest to defend. Attacking down from "
            "mountains adds weight to an attack, and passes make crossings cheaper."
        ),
    }
    articles = []
    for terrain in TERRAINS:
        rows = [
            [
                RECRUITS[kind]["name"],
                f"×{movement.terrain_cost[terrain] * _role_factor(kind, terrain):g}",
            ]
            for kind in RECRUITS
            if kind in LAND_KINDS
        ]
        articles.append(
            Article(
                id="terrain-" + terrain,
                title=terrain.title(),
                category="Terrain",
                summary=descriptions[terrain].split(":")[0].split(".")[0] + ".",
                body=[descriptions[terrain], "See [[movement]] and [[combat]]."],
                tables=[("Movement cost for each arm", ["Arm", "Cost"], rows)],
                facts=[
                    ("Movement cost", f"×{movement.terrain_cost[terrain]:g}"),
                    ("Defence", f"×{combat.terrain_defense[terrain]:g}"),
                ],
                see_also=["movement", "combat", "map-modes"],
            )
        )
    return articles


def _nation_articles(names: Mapping[str, str]) -> list[Article]:
    articles = []
    for nation in NATIONS.values():
        rows = [[trait.name, trait.effect] for trait in nation.traits]
        articles.append(
            Article(
                id="nation-" + nation.id,
                title=names.get(nation.id, nation.id),
                category="Nations",
                summary=nation.summary,
                body=[f"“{nation.motto}”", *nation.history],
                tables=[("National traits", ["Trait", "Effect"], rows)],
                facts=[
                    ("Ruler", nation.ruler),
                    ("Capital", nation.capital),
                    ("Government", nation.government),
                    ("Founded", str(nation.founded)),
                ],
                see_also=["nations", "traits", "world"],
                plate=("nation", nation.id),
            )
        )
    return articles


def _event_articles() -> list[Article]:
    articles = []
    for event in EVENTS.values():
        rows = [[option.label] for option in event.options]
        articles.append(
            Article(
                id="event-" + event.id,
                title=event.title,
                category="Events",
                summary=event.text.split(".")[0] + ".",
                body=[event.text],
                tables=[("Choices", ["Option"], rows)],
                see_also=["events"],
            )
        )
    return articles


def _index(article_id: str, title: str, category: str, summary: str, articles: list[Article]) -> Article:
    rows = [[f"[[{a.id}|{a.title}]]", a.summary] for a in articles]
    return Article(
        article_id, title, category, summary, body=[summary], tables=[(title, ["Article", "Summary"], rows)]
    )


# The library -----------------------------------------------------------------------------


def build(names: Mapping[str, str]) -> dict[str, Article]:
    """Every article by id. ``names`` gives each nation's display name."""
    articles = [
        Article(
            id=raw["id"],
            title=raw["title"],
            category=raw["category"],
            summary=fill(raw.get("summary", "")),
            body=[fill(paragraph) for paragraph in raw["body"]],
            see_also=raw.get("see_also", []),
        )
        for raw in load_content("text", "carsapedia.json")
    ]
    units, charters, buildings = _unit_articles(), _charter_articles(), _building_articles()
    terrains, nations, events = _terrain_articles(), _nation_articles(names), _event_articles()
    by_id = {a.id: a for a in articles}
    if "traits" in by_id:
        by_id["traits"].tables.append(
            (
                "Every national trait",
                ["Nation", "Trait", "Effect"],
                [
                    [f"[[nation-{n.id}|{names.get(n.id, n.id)}]]", t.name, t.effect]
                    for n in NATIONS.values()
                    for t in n.traits
                ],
            )
        )
    if "events" in by_id:
        by_id["events"].tables.append(
            ("Every event", ["Event", "Summary"], [[f"[[{a.id}|{a.title}]]", a.summary] for a in events])
        )
    if "charters" in by_id:
        by_id["charters"].tables.append(
            (
                "Every charter",
                ["Charter", "Arm", "Region"],
                [[f"[[{a.id}|{a.title}]]", a.facts[1][1], a.facts[0][1]] for a in charters],
            )
        )
    indexes = [
        _index(
            "nations",
            "The eight nations",
            "Nations",
            "The nations contesting the Americas, their histories and traits.",
            nations,
        ),
        _index(
            "units",
            "Units",
            "Units",
            "Every arm that can be raised, with its ratings, costs and upkeep.",
            units,
        ),
        _index(
            "buildings",
            "Buildings",
            "Buildings",
            "Every building a province can raise, with its costs.",
            buildings,
        ),
    ]
    articles += indexes + nations + units + charters + buildings + terrains + events
    library = {article.id: article for article in articles}
    _check_links(library)
    return library


def _check_links(library: dict[str, Article]) -> None:
    """A link to a missing article is a content error; fail loudly rather than show a dead link."""
    for article in library.values():
        texts = [
            *article.body,
            *(cell for _, _, rows in article.tables for row in rows for cell in row),
            *(v for _, v in article.facts),
        ]
        for text in texts:
            for match in LINK.finditer(text):
                if match.group(1) not in library:
                    raise ValueError(f"CARSapedia article {article.id!r} links to missing {match.group(1)!r}")
        for target in article.see_also:
            if target not in library:
                raise ValueError(f"CARSapedia article {article.id!r} lists missing {target!r}")


def search(library: dict[str, Article], query: str) -> list[Article]:
    """Articles containing every word of ``query``, titles matches first."""
    terms = query.casefold().split()
    matches = [a for a in library.values() if all(term in a.text().casefold() for term in terms)]
    return sorted(
        matches,
        key=lambda a: (
            not all(t in a.title.casefold() for t in terms),
            CATEGORIES.index(a.category) if a.category in CATEGORIES else 99,
            a.title,
        ),
    )
