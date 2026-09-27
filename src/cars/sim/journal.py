"""The campaign chronicle: a bounded, serializable log of what happened and where."""

from typing import TYPE_CHECKING

from cars.sim.calendar import date_label
from cars.sim.defines import DEFINES
from cars.sim.regional import unit_name

if TYPE_CHECKING:
    from cars.sim.state import GameState

LAND_BATTLE = "land battle"
NAVAL_BATTLE = "naval battle"
BATTLE_KINDS = (LAND_BATTLE, NAVAL_BATTLE)

# Unit id -> (owner, display name, hp), taken before a battle to report its losses.
Snapshot = dict[str, tuple[str, str, float]]
# What decided a battle, as (label, value) rows: ("River crossing", "x0.8").
Factors = tuple[tuple[str, str], ...]


def record(
    state: "GameState",
    kind: str,
    summary: str,
    location: str = "",
    details: list[str] | None = None,
    participants: list[str] | None = None,
) -> dict:
    entry = dict(
        round=state.round,
        date=date_label(state.clock),
        owner=state.active,
        kind=kind,
        summary=summary,
        location=location,
        details=details or [],
        participants=participants or [state.active],
    )
    state.reports.append(entry)
    del state.reports[: -DEFINES.journal.entry_limit]
    return entry


def snapshot(state: "GameState") -> Snapshot:
    return {unit.id: (unit.owner, unit_name(unit), unit.hp) for unit in state.units.values()}


def battle_report(
    state: "GameState",
    before: Snapshot,
    kind: str,
    summary: str,
    location: str,
    factors: Factors = (),
) -> dict:
    """Record a battle with its modifiers and every unit that lost strength since ``before``.

    Besides the plain-text details, the entry keeps ``factors`` as (label, value) rows
    and ``losses`` as (unit, owner, strength lost, strength left) rows for tables.
    """
    details, losses = [], []
    participants = {state.active}
    for unit_id, (owner, name, hp) in before.items():
        survivor = state.units.get(unit_id)
        lost = hp - (survivor.hp if survivor else 0)
        if lost > 0:
            participants.add(owner)
            left = "destroyed" if survivor is None else f"{survivor.hp:.1f}"
            outcome = left if survivor is None else left + " left"
            details.append(f"{unit_id}: -{lost:.1f} strength / {outcome}")
            losses.append([name, owner, f"{lost:.1f}", left])
    entry = record(state, kind, summary, location, details, sorted(participants))
    entry["factors"] = [list(row) for row in factors]
    entry["losses"] = losses
    return entry
