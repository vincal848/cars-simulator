"""The campaign chronicle: a bounded, serializable log of what happened and where."""

from typing import TYPE_CHECKING

from cars.sim.calendar import date_label
from cars.sim.defines import DEFINES

if TYPE_CHECKING:
    from cars.sim.state import GameState

LAND_BATTLE = "land battle"
NAVAL_BATTLE = "naval battle"
AIR_STRIKE = "air strike"
BATTLE_KINDS = (LAND_BATTLE, NAVAL_BATTLE, AIR_STRIKE)

# Unit id -> (owner, kind, hp), taken before a battle to report its losses.
Snapshot = dict[str, tuple[str, str, float]]


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
    return {unit.id: (unit.owner, unit.kind, unit.hp) for unit in state.units.values()}


def battle_report(
    state: "GameState",
    before: Snapshot,
    kind: str,
    summary: str,
    location: str,
    factors: str = "",
) -> dict:
    """Record a battle, listing every unit that lost strength since ``before``."""
    losses = []
    participants = {state.active}
    for unit_id, (owner, _kind, hp) in before.items():
        survivor = state.units.get(unit_id)
        lost = hp - (survivor.hp if survivor else 0)
        if lost > 0:
            participants.add(owner)
            outcome = " / destroyed" if survivor is None else f" / {survivor.hp:.1f} left"
            losses.append(f"{unit_id}: -{lost:.1f} strength{outcome}")
    if factors:
        losses.insert(0, factors)
    return record(state, kind, summary, location, losses, sorted(participants))
