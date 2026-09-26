"""Filesystem locations for bundled game content and per-user data."""

import json
import os
import sys
from pathlib import Path
from typing import Any

CONTENT_DIR = Path(__file__).resolve().parent / "content"


def content_path(*parts: str) -> Path:
    return CONTENT_DIR.joinpath(*parts)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_content(*parts: str) -> Any:
    """Parse a bundled JSON file, e.g. ``load_content("common", "units.json")``."""
    return read_json(content_path(*parts))


def write_text_atomic(path: Path, text: str) -> None:
    """Write through a temporary file so a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _platform_data_dir() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        return Path(local) / "CARS"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CARS"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "cars"


def saves_dir() -> Path:
    """Campaign saves; ``CARS_SAVE_DIR`` relocates all user data (used by tests)."""
    override = os.environ.get("CARS_SAVE_DIR")
    if override:
        return Path(override).expanduser()
    return _platform_data_dir() / "saves"


def replays_dir() -> Path:
    return saves_dir().parent / "replays"


def settings_path() -> Path:
    return saves_dir().parent / "settings.json"


def crash_log_path() -> Path:
    return saves_dir().parent / "crash.log"
