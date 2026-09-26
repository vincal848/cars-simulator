"""Regenerate the golden references after an intentional change.

    python -m tests.golden.update             # rewrite both reference files
    python -m tests.golden.update --dump out  # also write every payload and screenshot to out/

Dumping at two commits and diffing the folders shows exactly what changed.
Screen references are only meaningful on the machine that records them; the test
skips them wherever pygame, SDL or the system fonts differ.
"""

import argparse
from pathlib import Path

import tests.support  # noqa: F401  (headless SDL and an isolated user profile)
from tests.golden.reference import SCREENS_FILE, SIMULATION_FILE, save, screen_hashes, simulation_hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dump", type=Path, help="Also write payloads and screenshots to this folder")
    parser.add_argument("--simulation-only", action="store_true", help="Leave the screen references alone")
    args = parser.parse_args()
    if args.dump:
        args.dump.mkdir(parents=True, exist_ok=True)
    steps = simulation_hashes(args.dump)
    save(SIMULATION_FILE, {"steps": steps})
    print(f"{len(steps)} simulation steps -> {SIMULATION_FILE}")
    if not args.simulation_only:
        env, screens = screen_hashes(args.dump)
        save(SCREENS_FILE, {"environment": env, "screens": screens})
        print(f"{len(screens)} screens -> {SCREENS_FILE}")


if __name__ == "__main__":
    main()
