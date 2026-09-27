"""Filesystem locations for bundled game content, mods and per-user data.

Mods are folders in ``<user data>/mods/`` that mirror the ``content`` layout. They
load alphabetically: JSON objects are merged key by key over the bundled file
(so a mod can change a single define), anything else replaces it outright.
"""

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


def merge(base: Any, override: Any) -> Any:
    """Deep-merge JSON objects; any other value in ``override`` replaces ``base``."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = merge(base[key], value) if key in base else value
        return merged
    return override


def load_content(*parts: str) -> Any:
    """Parse a content JSON file with every active mod layered on top.

    For example ``load_content("common", "units.json")``.
    """
    data = read_json(content_path(*parts))
    for mod in active_mods():
        override = mod.joinpath(*parts)
        if override.is_file():
            data = merge(data, read_json(override))
    return data


def find_asset(*parts: str) -> Path | None:
    """A bundled or modded file such as an image; the last active mod that has it wins."""
    for mod in reversed(active_mods()):
        candidate = mod.joinpath(*parts)
        if candidate.is_file():
            return candidate
    bundled = content_path(*parts)
    return bundled if bundled.is_file() else None


def mods_dir() -> Path:
    return saves_dir().parent / "mods"


def active_mods() -> list[Path]:
    folder = mods_dir()
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir() if path.is_dir())


def mod_files(folder: str, pattern: str = "*.json") -> list[Path]:
    """Files that mods add to a content folder, in load order."""
    return [path for mod in active_mods() for path in sorted((mod / folder).glob(pattern))]


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
