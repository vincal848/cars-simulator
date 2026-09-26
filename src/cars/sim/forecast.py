"""Order forecasts: run the real rules on a throwaway copy of the state."""

from copy import deepcopy
from typing import TYPE_CHECKING

from cars.sim.air import mission
from cars.sim.journal import BATTLE_KINDS
from cars.sim.orders import issue_move

if TYPE_CHECKING:
    from cars.sim.state import GameState

MOVE = "move"


def forecast_order(state: "GameState", unit_id: str, target: str, mode: str = MOVE) -> dict:
    """Predicted outcome of an order, without changing ``state``.

    ``mode`` is ``"move"`` or an air mission (strike, support, rebase).
    """
    trial = deepcopy(state)
    # The journal is bounded, so isolate this order's entries instead of diffing lengths.
    trial.reports = []
    if mode == MOVE:
        route, message = issue_move(trial, unit_id, target)
        accepted = bool(route)
    else:
        accepted, message = mission(trial, unit_id, target, mode)
    battles = [r for r in trial.reports if r["kind"] in BATTLE_KINDS]

    owner = state.units[unit_id].owner
    own_loss = enemy_loss = 0
    destroyed = 0
    for unit in state.units.values():
        survivor = trial.units.get(unit.id)
        damage = unit.hp - (survivor.hp if survivor else 0)
        if damage <= 0:
            continue
        if unit.owner == owner:
            own_loss += damage
        else:
            enemy_loss += damage
            destroyed += survivor is None
    factors = battles[0]["details"][0] if battles and battles[0]["details"] else ""
    return dict(
        accepted=accepted,
        message=message.split(" Terrain")[0],
        own_loss=own_loss,
        enemy_loss=enemy_loss,
        destroyed=destroyed,
        factors=factors,
    )


def signature(state: "GameState") -> tuple:
    """Everything a forecast depends on; cheap enough to key a per-frame hover cache."""
    units = tuple(
        (u.id, u.owner, u.kind, u.location, u.hp, u.remaining, u.attack, u.defense, u.supplied)
        for u in state.units.values()
    )
    provinces = tuple(
        (p.id, p.controller, p.terrain, tuple(p.buildings.items()), tuple(p.local_modifiers.items()))
        for p in state.provinces.values()
    )
    support = tuple((m["unit"], m["owner"], m["target"]) for m in state.air_support)
    return state.active, state.round, units, provinces, support
