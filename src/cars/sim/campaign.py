"""The single-player boundary: the human may only command their own faction on their own turn.

Successful commands are forwarded to a replay recorder when one is attached.
"""

from typing import TYPE_CHECKING, Protocol

from cars.sim import air, buildings, diplomacy, events, market, recruitment
from cars.sim.objectives import announce_stage, begin
from cars.sim.orders import issue_move

if TYPE_CHECKING:
    from cars.sim.state import GameState


class CommandRecorder(Protocol):
    def append(self, state: "GameState", action: str, args: tuple) -> None: ...


class Campaign:
    def __init__(self, state: "GameState") -> None:
        self.state = state
        self.player: str | None = None
        self.recorder: CommandRecorder | None = None

    def choose(self, faction: str) -> bool:
        """Take command of ``faction``. A campaign's faction can be chosen only once."""
        if self.player is not None or faction not in self.state.factions:
            return False
        self.player = faction
        begin(self.state, faction)
        self.state.active_index = list(self.state.factions).index(faction)
        announce_stage(self.state)
        return True

    @property
    def human_turn(self) -> bool:
        return self.player is not None and self.state.active == self.player

    def _recorded(self, action: str, args: tuple, result: tuple) -> tuple:
        if self.recorder and result[0]:
            self.recorder.append(self.state, action, args)
        return result

    def move(self, unit_id: str, destination: str) -> tuple[list[str], str]:
        unit = self.state.units.get(unit_id)
        if not self.human_turn or unit is None or unit.owner != self.player:
            return [], "You can command only your own faction."
        result = issue_move(self.state, unit_id, destination)
        return self._recorded("move", (unit_id, destination), result)

    def construct(self, province: str, kind: str) -> tuple[bool, str]:
        if not self.human_turn:
            return False, "Wait for your faction turn."
        result = buildings.build(self.state, province, kind)
        return self._recorded("build", (province, kind), result)

    def recruit(self, province: str, kind: str) -> tuple[str | None, str]:
        if not self.human_turn:
            return None, "Wait for your faction turn."
        result = recruitment.recruit(self.state, province, kind)
        return self._recorded("recruit", (province, kind), result)

    def trade(self, resource: str, side: str) -> tuple[bool, str]:
        if not self.human_turn:
            return False, "Trade on your own turn."
        result = market.trade(self.state, self.player, resource, side)
        return self._recorded("trade", (resource, side), result)

    def propose_peace(self, faction: str) -> tuple[bool, str]:
        if not self.human_turn:
            return False, "Wait for your faction turn."
        result = diplomacy.propose_peace(self.state, self.player, faction)
        return self._recorded("peace", (faction,), result)

    def declare_war(self, faction: str) -> tuple[bool, str]:
        if not self.human_turn:
            return False, "Wait for your faction turn."
        result = diplomacy.declare_war(self.state, self.player, faction)
        return self._recorded("war", (faction,), result)

    def choose_event_option(self, event_id: str, index: int) -> tuple[bool, str]:
        if not self.human_turn:
            return False, "Wait for your faction turn."
        result = events.choose_option(self.state, self.player, event_id, index)
        return self._recorded("event", (event_id, str(index)), result)

    def air_mission(self, unit_id: str, target: str, kind: str) -> tuple[bool, str]:
        if not self.human_turn:
            return False, "Wait for your faction turn."
        result = air.mission(self.state, unit_id, target, kind)
        return self._recorded("air", (unit_id, target, kind), result)
