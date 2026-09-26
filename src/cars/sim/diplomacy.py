"""War and peace between factions.

Every pair of factions starts at war. A rival accepts peace only when it is no
stronger than the faction offering it. Peace forbids entering each other's
provinces or attacking each other's forces, and holds for a truce period before
either side may declare war again.
"""

from typing import TYPE_CHECKING

from cars.sim.defines import DEFINES
from cars.sim.journal import record
from cars.sim.state import PEACE, relation_key

if TYPE_CHECKING:
    from cars.sim.state import GameState

RULES = DEFINES.diplomacy
DIPLOMACY = "diplomacy"


def military_strength(state: "GameState", faction: str) -> float:
    """Combined attack and defence of every unit, scaled by current strength."""
    return sum(u.attack_power() + u.defense_power() for u in state.units.values() if u.owner == faction)


def truce_ends(state: "GameState", a: str, b: str) -> int | None:
    """The first round either side may break the peace, or None when at war."""
    relation = state.relation(a, b)
    if relation["status"] != PEACE:
        return None
    return relation["since"] + RULES.truce_rounds


def quote_peace(state: "GameState", proposer: str, target: str) -> str:
    """Why ``target`` would refuse peace with ``proposer`` (empty if it accepts)."""
    if proposer != state.active or target not in state.factions or target == proposer:
        return "Choose another nation."
    if not state.at_war(proposer, target):
        return "You are already at peace."
    if military_strength(state, target) > military_strength(state, proposer) * RULES.peace_strength_ratio:
        return f"{state.factions[target].name} feels strong enough to fight on."
    return ""


def propose_peace(state: "GameState", proposer: str, target: str) -> tuple[bool, str]:
    refusal = quote_peace(state, proposer, target)
    if refusal:
        return False, refusal
    state.relations[relation_key(proposer, target)] = {"status": PEACE, "since": state.round}
    # Close air support can no longer be flown over the new partner's territory.
    partners = {proposer, target}
    state.air_support = [
        order
        for order in state.air_support
        if {order["owner"], state.provinces[order["target"]].controller} != partners
    ]
    names = f"{state.factions[proposer].name} and {state.factions[target].name}"
    record(state, DIPLOMACY, f"Peace between {names}.", participants=[proposer, target])
    return True, f"Peace signed with {state.factions[target].name}."


def quote_war(state: "GameState", declarer: str, target: str) -> str:
    """Why ``declarer`` cannot declare war on ``target`` now (empty if it can)."""
    if declarer != state.active or target not in state.factions or target == declarer:
        return "Choose another nation."
    ends = truce_ends(state, declarer, target)
    if ends is None:
        return "You are already at war."
    if state.round < ends:
        return f"The truce holds until round {ends}."
    return ""


def declare_war(state: "GameState", declarer: str, target: str) -> tuple[bool, str]:
    refusal = quote_war(state, declarer, target)
    if refusal:
        return False, refusal
    del state.relations[relation_key(declarer, target)]
    message = f"{state.factions[declarer].name} declares war on {state.factions[target].name}."
    record(state, DIPLOMACY, message, participants=[declarer, target])
    return True, message


def wants_war(state: "GameState", declarer: str, target: str) -> bool:
    """Whether a rival would break the peace: only once the truce ends, and when much stronger."""
    if quote_war(state, declarer, target):
        return False
    return military_strength(state, declarer) > military_strength(state, target) * RULES.war_strength_ratio
