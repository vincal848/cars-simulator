"""Re-record a replay under the current rules after a deliberate rule change.

    python tools/rerecord_replay.py examples/opening.json

The starting snapshot and the player's commands are kept; each command is replayed
with today's rules and stamped with a fresh state hash and the current RULESET.
Commands that the new rules refuse are dropped and listed.
"""

import argparse
import json
from copy import deepcopy
from pathlib import Path

from cars.persist.replay import REPLAY_VERSION, RULESET, apply_command, digest
from cars.persist.savegame import decode_game


def rerecord(data: dict) -> tuple[dict, list[dict]]:
    state, *_ = decode_game(deepcopy(data["initial"]))
    commands, dropped = [], []
    for command in data["commands"]:
        before = digest(state)
        apply_command(state, command["action"], command["args"])
        if digest(state) == before:
            dropped.append(command)
            continue
        commands.append(dict(action=command["action"], args=command["args"], after=digest(state)))
    replay = dict(version=REPLAY_VERSION, ruleset=RULESET, initial=data["initial"], commands=commands)
    return replay, dropped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("replay", type=Path)
    args = parser.parse_args()
    replay, dropped = rerecord(json.loads(args.replay.read_text(encoding="utf-8")))
    args.replay.write_text(json.dumps(replay), encoding="utf-8")
    print(f"{len(replay['commands'])} commands re-recorded under ruleset {RULESET}")
    for command in dropped:
        print("  dropped (now refused):", command["action"], command["args"])


if __name__ == "__main__":
    main()
