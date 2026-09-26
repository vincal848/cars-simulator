"""Verified command replays.

A replay stores the starting snapshot and every successful player command, each
with a hash of the state it produced. Playback re-runs the commands on a
separate copy and stops at the first divergence. Replay files are data only:
commands are looked up by name, never executed as code.
"""

import hashlib
import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from cars.paths import replays_dir, write_text_atomic
from cars.persist.savegame import decode_game, encode_game
from cars.sim.ai import faction_actions
from cars.sim.air import mission
from cars.sim.buildings import build
from cars.sim.market import trade
from cars.sim.orders import issue_move
from cars.sim.recruitment import recruit
from cars.sim.state import FACTION_COUNT, GameState
from cars.sim.turn import end_turn

REPLAY_VERSION = 1
# Bump whenever a rule change would alter the outcome of a recorded command.
RULESET = "0.23"
MAX_COMMANDS = 20_000
MAX_FILE_BYTES = 50_000_000


def digest(state: GameState) -> str:
    """Hash of everything that affects play; UI-only state is deliberately excluded."""
    data = {
        name: [asdict(item) for item in getattr(state, name).values()]
        for name in ("provinces", "regions", "cities", "factions", "units")
    }
    data.update(
        active=state.active_index,
        round=state.round,
        clock=state.clock,
        objectives=state.objectives,
        market=state.market,
        recruited=state.recruited,
        air_support=state.air_support,
        reports=state.reports,
    )
    encoded = json.dumps(data, sort_keys=True, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _end_round(state: GameState) -> None:
    """The player's End Turn, followed by every rival turn."""
    player = state.active
    end_turn(state)
    for _ in range(FACTION_COUNT - 1):
        for _action in faction_actions(state):
            pass
        end_turn(state)
    if state.active != player:
        raise ValueError("Replay turn order failed.")


# Command name -> (argument count, handler).
COMMANDS: dict[str, tuple[int, Callable[..., object]]] = {
    "move": (2, issue_move),
    "build": (2, build),
    "recruit": (2, recruit),
    "air": (3, mission),
    "trade": (2, lambda state, resource, side: trade(state, state.active, resource, side)),
    "end_turn": (0, _end_round),
}


def apply_command(state: GameState, action: object, args: object) -> None:
    valid = (
        isinstance(action, str)
        and action in COMMANDS
        and isinstance(args, list)
        and len(args) == COMMANDS[action][0]
        and all(isinstance(arg, str) for arg in args)
    )
    if not valid:
        raise ValueError("Invalid replay command.")
    COMMANDS[action][1](state, *args)


class Recorder:
    """Collects the current session's commands, starting from a snapshot."""

    def __init__(self, state: GameState, shapes: dict, seas: list, player: str) -> None:
        self.initial = deepcopy(encode_game(state, shapes, seas, player))
        self.commands: list[dict] = []

    def append(self, state: GameState, action: str, args: tuple) -> None:
        self.commands.append(dict(action=action, args=list(args), after=digest(state)))

    def data(self) -> dict:
        return dict(
            version=REPLAY_VERSION,
            ruleset=RULESET,
            initial=deepcopy(self.initial),
            commands=deepcopy(self.commands),
        )

    def export(self, path: Path | None = None) -> Path:
        path = path or latest_export_path()
        write_text_atomic(path, json.dumps(self.data()))
        return path


def latest_export_path() -> Path:
    return replays_dir() / "latest.json"


def read_replay_file(path: Path) -> dict:
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Replay file is too large.")
    return json.loads(path.read_text(encoding="utf-8"))


class Playback:
    """Steps through a replay on its own state, verifying each command's result."""

    def __init__(self, data: dict) -> None:
        if (
            not isinstance(data, dict)
            or data.get("version") != REPLAY_VERSION
            or data.get("ruleset") != RULESET
        ):
            raise ValueError(f"Replay requires the same {RULESET} ruleset.")
        if not isinstance(data.get("commands"), list) or len(data["commands"]) > MAX_COMMANDS:
            raise ValueError("Invalid replay length.")
        self.data = deepcopy(data)
        self.reset()

    @property
    def commands(self) -> list:
        return self.data["commands"]

    def reset(self) -> None:
        self.state, self.shapes, self.seas, self.player = decode_game(deepcopy(self.data["initial"]))
        self.index = 0
        self.message = "Initial campaign state"
        self.failed = False

    def step(self) -> bool:
        """Apply the next command. Returns False at the end; raises ValueError on divergence."""
        if self.failed or self.index >= len(self.commands):
            return False
        try:
            return self._step()
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            self.failed = True
            raise ValueError(str(exc)) from exc

    def _step(self) -> bool:
        command = self.commands[self.index]
        if not isinstance(command, dict):
            raise ValueError("Invalid replay entry.")
        trial = deepcopy(self.state)
        apply_command(trial, command.get("action"), command.get("args"))
        if digest(trial) != command.get("after"):
            raise ValueError(f"Replay diverged at command {self.index + 1}. Playback stopped.")
        self.state = trial
        self.index += 1
        label = command["action"].replace("_", " ").title()
        self.message = f"{self.index}: {label} / " + " / ".join(command["args"])
        return True
