"""The dominion objective and the campaign stages derived from it.

The player wins by holding a number of cities for consecutive full rounds. The
streak is counted when the player's turn begins and resets on any shortfall.
"""

from typing import TYPE_CHECKING, NamedTuple

from cars.sim.entities import City
from cars.sim.journal import record

if TYPE_CHECKING:
    from cars.sim.state import GameState

DEFAULT_RULES = dict(cities=3, turns=5)
ACTIVE, VICTORY, DEFEAT = "active", "victory", "defeat"


class Stage(NamedTuple):
    index: int
    name: str
    goal: str


def controlled_cities(state: "GameState", player: str) -> list[City]:
    return [c for c in state.cities.values() if state.provinces[c.province].controller == player]


def begin(state: "GameState", player: str) -> None:
    """Start tracking the objective for ``player``; a no-op if already started."""
    if state.objectives.get("player"):
        return
    rules = state.objectives.get("rules", DEFAULT_RULES).copy()
    if any(not isinstance(rules.get(key), int) or rules[key] < 1 for key in ("cities", "turns")):
        raise ValueError("Objective targets must be positive integers.")
    state.objectives = dict(rules=rules, player=player, held=0, status=ACTIVE)


def evaluate(state: "GameState", tick: bool = False) -> None:
    """Update victory/defeat. ``tick`` counts a completed round towards the streak."""
    goal = state.objectives
    if not goal.get("player") or goal["status"] != ACTIVE:
        return
    player = goal["player"]
    cities = controlled_cities(state, player)
    has_army = any(u.owner == player and u.is_land for u in state.units.values())
    if not cities and not has_army:
        goal["status"] = DEFEAT
    if len(cities) < goal["rules"]["cities"]:
        goal["held"] = 0
    elif tick:
        goal["held"] += 1
        if goal["held"] >= goal["rules"]["turns"]:
            goal["status"] = VICTORY
    announce_stage(state)


def campaign_stage(state: "GameState") -> Stage:
    goal = state.objectives
    player = goal.get("player")
    if not player:
        return Stage(0, "Choose a realm", "Select a faction to begin its campaign.")
    if goal["status"] == DEFEAT:
        return Stage(0, "Realm fallen", "Your campaign has ended in defeat; you may continue the sandbox.")
    if goal["status"] == VICTORY:
        return Stage(3, "Dominion", "Victory secured. Continue shaping your realm at your own pace.")
    cities = len(controlled_cities(state, player))
    needed = goal["rules"]["cities"]
    if cities == 0:
        return Stage(0, "Foothold", "Capture a city and establish a secure base.")
    if cities < needed:
        return Stage(1, "Expansion", f"Control {needed - cities} more cities to begin consolidation.")
    remaining = max(0, goal["rules"]["turns"] - goal["held"])
    return Stage(2, "Consolidation", f"Keep at least {needed} cities for {remaining} more full rounds.")


def announce_stage(state: "GameState") -> None:
    """Journal a milestone whenever the campaign stage changes."""
    player = state.objectives.get("player")
    if not player:
        return
    stage = campaign_stage(state)
    key = DEFEAT if state.objectives["status"] == DEFEAT else stage.name
    if state.objectives.get("stage") != key:
        state.objectives["stage"] = key
        record(
            state,
            "milestone",
            "Campaign stage: " + stage.name,
            details=[stage.goal],
            participants=[player],
        )
