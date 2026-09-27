"""Reading, computing and writing the golden references."""

import hashlib
import json
from pathlib import Path

import pygame

from tests.golden.runs import environment, fingerprint, screen_runs, simulation_runs
from tests.support import SCREEN_SIZE

# The smallest supported window at 100%, and a 1080p screen at the default 125%.
SCREEN_SIZES = (SCREEN_SIZE, (1920, 1080))

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
SIMULATION_FILE = REFERENCE_DIR / "simulation.json"
SCREENS_FILE = REFERENCE_DIR / "screens.json"


def simulation_hashes(dump: Path | None = None) -> list[list[str]]:
    hashes = []
    for i, (label, payload) in enumerate(simulation_runs()):
        hashes.append([label, fingerprint(payload)])
        if dump:
            text = json.dumps(payload, sort_keys=True, indent=1, default=repr)
            (dump / f"sim-{i:04}.json").write_text(text, encoding="utf-8")
    return hashes


def screen_hashes(dump: Path | None = None) -> tuple[dict, list[list[str]]]:
    """Render every reference screen on a hidden display, at each reference window size;
    returns (environment, hashes)."""
    pygame.init()
    try:
        env = environment(pygame.font.SysFont("georgia", 15, italic=True))
        hashes = []
        for width, height in SCREEN_SIZES:
            screen = pygame.display.set_mode((width, height))
            for i, (label, surface) in enumerate(screen_runs(screen)):
                label = f"{width}x{height} {label}"
                hashes.append([label, hashlib.sha256(pygame.image.tobytes(surface, "RGB")).hexdigest()])
                if dump:
                    pygame.image.save(
                        surface,
                        str(dump / f"screen-{width}-{i:02}-{label.split(' ', 1)[1].replace(' ', '-')}.png"),
                    )
        return env, hashes
    finally:
        pygame.quit()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")
