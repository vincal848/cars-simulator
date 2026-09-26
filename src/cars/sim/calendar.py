"""Campaign time. A date spans one full round, so every faction acts once per season."""

from typing import TYPE_CHECKING

from cars.paths import load_content

if TYPE_CHECKING:
    from cars.sim.state import GameState

_DEFAULTS = load_content("common", "calendar.json")
MAX_PERIODS = 12
MAX_PERIOD_NAME = 24


def new_clock() -> dict:
    return dict(start_year=_DEFAULTS["start_year"], periods=list(_DEFAULTS["periods"]), elapsed=0)


def validate_clock(clock: object) -> None:
    valid = (
        isinstance(clock, dict)
        and type(clock.get("start_year")) is int
        and clock["start_year"] >= 1
        and type(clock.get("elapsed")) is int
        and clock["elapsed"] >= 0
        and isinstance(clock.get("periods"), list)
        and 1 <= len(clock["periods"]) <= MAX_PERIODS
        and all(isinstance(p, str) and len(p) <= MAX_PERIOD_NAME for p in clock["periods"])
    )
    if not valid:
        raise ValueError("Invalid campaign calendar.")


def date_label(clock: dict, ahead: int = 0) -> str:
    """A label such as "Spring 1800", optionally ``ahead`` rounds in the future."""
    elapsed = clock["elapsed"] + ahead
    periods = clock["periods"]
    year = clock["start_year"] + elapsed // len(periods)
    return f"{periods[elapsed % len(periods)]} {year}".strip()


def turn_phase(state: "GameState") -> tuple[str, int]:
    """Who is acting, and how many rivals have finished since the player's turn."""
    player = state.objectives.get("player")
    if not player:
        return "Awaiting your realm", 0
    if state.active == player:
        return "Your orders", 0
    order = list(state.factions)
    completed = (order.index(state.active) - order.index(player)) % len(order)
    return state.factions[state.active].name, completed - 1
