"""Ending a faction's turn: collect income, hand over to the next faction, advance time."""

from typing import TYPE_CHECKING

from cars.sim.calendar import date_label
from cars.sim.economy import produce
from cars.sim.journal import record
from cars.sim.market import replenish, treasury_income
from cars.sim.objectives import evaluate
from cars.sim.recovery import recover
from cars.sim.supply import refresh_supply
from cars.sim.upkeep import pay_upkeep

if TYPE_CHECKING:
    from cars.sim.state import GameState


def end_turn(state: "GameState") -> dict[str, float]:
    """Finish the active faction's turn and return the resources it produced."""
    finishing = state.factions[state.active]
    finishing.gold += treasury_income(state, state.active)
    gains = produce(state, state.active)
    details = [f"{resource}: +{amount:.1f}" for resource, amount in gains.items()]
    record(state, "economy", "Turn completed; production collected.", details=details)
    pay_upkeep(state, state.active)
    state.recruited.clear()

    state.active_index = (state.active_index + 1) % len(state.factions)
    if state.active_index == 0:
        state.round += 1
        replenish(state)
    # Close air support lasts until the ordering faction's next turn.
    state.air_support = [
        order
        for order in state.air_support
        if order["owner"] != state.active and order["unit"] in state.units
    ]
    refresh_supply(state)
    for unit in state.units.values():
        if unit.owner == state.active:
            unit.remaining = unit.allowance
    recover(state, state.active)

    player = state.player
    if state.active == player or (not player and state.active_index == 0):
        state.clock["elapsed"] += 1
        if player:
            record(
                state,
                "calendar",
                date_label(state.clock) + " begins.",
                details=["Orders refreshed. The next campaign round is ready."],
                participants=[player],
            )
    evaluate(state, tick=state.active == player)
    return gains
