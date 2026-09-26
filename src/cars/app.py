"""Command-line entry point and main loop."""

import argparse
import os
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="cars", description="C.A.R.S. - Combat Arms Region Simulator")
    parser.add_argument("--scenario", type=Path, help="Scenario JSON path")
    parser.add_argument("--smoke", action="store_true", help="Render a few frames without opening a window")
    parser.add_argument("--screenshot", type=Path, help="Save the last rendered frame as a PNG")
    parser.add_argument("--faction", choices=[f"f{i}" for i in range(8)], help="Skip faction selection")
    parser.add_argument("--fullscreen-windowed", action="store_true", help="Open borderless at desktop size")
    parser.add_argument("--tutorial", action="store_true", help="Start the guided tutorial campaign")
    parser.add_argument("--replay", type=Path, help="Open a replay JSON file")
    parser.add_argument(
        "replay_file", nargs="?", type=Path, help="Replay file (supports drag-and-drop onto the executable)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.smoke:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    # pygame reads the SDL environment when imported, so import it only after the flags above.
    import pygame

    from cars.ui.app import App

    pygame.init()
    App(args).run()
    pygame.quit()


if __name__ == "__main__":
    main()
