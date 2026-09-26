"""Regional charters: named formations that keep a base role but move faster in one terrain."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cars.paths import load_content

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.state import GameState


@dataclass(frozen=True)
class Charter:
    id: str
    name: str
    region: str
    kind: str
    terrain: str
    discount: float
    history: str
    style: str


CHARTERS: dict[str, Charter] = {
    key: Charter(id=key, **spec) for key, spec in load_content("common", "regional_units.json").items()
}


def unit_name(unit: "Unit") -> str:
    charter = CHARTERS.get(unit.regional)
    return charter.name if charter else unit.kind.title()


def charter_for(state: "GameState", province: str) -> Charter | None:
    """The charter recruitable in ``province``'s region, if any.

    Scenario region IDs are local (r0, r1...), so charters match on region name.
    """
    name = state.regions[state.provinces[province].region_id].name
    return next((charter for charter in CHARTERS.values() if charter.region == name), None)
