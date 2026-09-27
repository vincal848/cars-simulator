"""Synthesized sound effects and the offline classical music collection.

Audio is optional: without a device the game plays on silently.
"""

import json
import math
import random
from array import array
from pathlib import Path
from typing import ClassVar

import pygame

from cars.paths import content_path, read_json, settings_path, write_text_atomic
from cars.ui.kit.ui import SCALES
from cars.ui.typography import DEFAULT_FONT, FONT_CHOICES

MUSIC_DIR = content_path("music")
EFFECT_NOTES = {
    "click": [440, 660],
    "move": [220, 330],
    "battle": [100, 83, 65],
    "build": [330, 440, 660],
    "turn": [330, 494, 660],
}
NOTE_SECONDS = 0.10
FADE_IN_MS = 600
VOLUMES = ("master", "effects", "music")
TOGGLES = ("autosave", "paused", "shuffle")


class Audio:
    DEFAULTS: ClassVar[dict] = dict(
        master=0.6,
        effects=0.7,
        music=0.25,
        autosave=True,
        track=0,
        paused=False,
        shuffle=False,
        ui_scale=0,  # 0 follows the window size
        font=DEFAULT_FONT,
    )

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings_path()
        self.settings = self.DEFAULTS.copy()
        self.available = False
        self.error = ""
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music_channel = pygame.mixer.music
        self.music_folder = MUSIC_DIR
        try:
            self.tracks: list[dict] = read_json(MUSIC_DIR / "collection.json")
        except (OSError, ValueError):
            self.tracks = []
        self.index = 0
        self.music_loaded = False
        self._load_settings()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2)
            self.available = True
            for name, notes in EFFECT_NOTES.items():
                self.sounds[name] = _synthesize(notes, NOTE_SECONDS)
            self.index = self.settings["track"] % len(self.tracks) if self.tracks else 0
            self.start(self.index)
            self.apply()
        except (pygame.error, ValueError):
            self.available = False
            self.error = "No audio device; play continues silently."

    def _load_settings(self) -> None:
        """Adopt valid saved preferences; anything malformed keeps its default."""
        try:
            values = read_json(self.path)
            for key in VOLUMES:
                value = values.get(key)
                if isinstance(value, (int, float)) and math.isfinite(value):
                    self.settings[key] = max(0, min(1, value))
            for key in TOGGLES:
                if isinstance(values.get(key), bool):
                    self.settings[key] = values[key]
            if type(values.get("track")) is int:
                self.settings["track"] = values["track"]
            if values.get("ui_scale") in (0, *SCALES):
                self.settings["ui_scale"] = values["ui_scale"]
            if values.get("font") in range(len(FONT_CHOICES)):
                self.settings["font"] = values["font"]
        except (OSError, ValueError, AttributeError):
            pass

    def apply(self) -> None:
        if not self.available:
            return
        for sound in self.sounds.values():
            sound.set_volume(self.settings["master"] * self.settings["effects"])
        self.music_channel.set_volume(self.settings["master"] * self.settings["music"])

    def change(self, key: str, delta: float = 0) -> None:
        """Toggle a switch, or nudge a volume by ``delta`` within 0..1."""
        if key in ("autosave", "shuffle"):
            self.settings[key] = not self.settings[key]
        else:
            self.settings[key] = round(max(0, min(1, self.settings[key] + delta)), 2)
        self.apply()
        self.persist()

    def set(self, key: str, value) -> None:
        """Store a preference that is not a volume or switch, such as the UI scale."""
        self.settings[key] = value
        self.persist()

    def persist(self) -> None:
        try:
            write_text_atomic(self.path, json.dumps(self.settings))
        except OSError:
            self.error = "Settings changed for this session; could not save preferences."

    def play(self, name: str) -> None:
        if self.available and name in self.sounds:
            self.sounds[name].play()

    @property
    def current(self) -> dict | None:
        return self.tracks[self.index] if self.tracks else None

    def start(self, index: int) -> bool:
        """Play track ``index``, skipping unreadable files once each."""
        self.music_loaded = False
        if not self.available or not self.tracks:
            return False
        self.music_channel.stop()
        for offset in range(len(self.tracks)):
            candidate = (index + offset) % len(self.tracks)
            try:
                self.music_channel.load(str(MUSIC_DIR / self.tracks[candidate]["file"]))
                self.music_channel.play(fade_ms=FADE_IN_MS)
            except (pygame.error, OSError):
                self.error = "A recording could not be opened; unavailable tracks are skipped."
                continue
            self.index = candidate
            self.settings["track"] = candidate
            self.music_loaded = True
            if self.settings["paused"]:
                self.music_channel.pause()
            self.apply()
            return True
        self.error = "Music files unavailable. Sound effects remain enabled."
        return False

    def select(self, index: int) -> None:
        if not 0 <= index < len(self.tracks):
            return
        self.settings["paused"] = False
        self.start(index)
        self.persist()

    def skip(self, direction: int = 1) -> None:
        if not self.tracks:
            return
        others = [i for i in range(len(self.tracks)) if i != self.index]
        if self.settings["shuffle"] and others:
            index = random.choice(others)
        else:
            index = (self.index + direction) % len(self.tracks)
        self.start(index)
        self.persist()

    def toggle_pause(self) -> None:
        self.settings["paused"] = not self.settings["paused"]
        if self.available and self.music_loaded:
            if self.settings["paused"]:
                self.music_channel.pause()
            else:
                self.music_channel.unpause()
        self.persist()

    def update(self) -> None:
        """Advance to the next recording when one finishes. Called every frame on every screen."""
        playing = self.available and self.music_loaded and not self.settings["paused"]
        if playing and not self.music_channel.get_busy():
            self.skip()


def _synthesize(notes: list[int], duration: float) -> pygame.mixer.Sound:
    """A short enveloped chime, one note after another."""
    rate, sample_format, channels = pygame.mixer.get_init()
    if sample_format != -16:
        raise ValueError("Unsupported audio format")
    samples = array("h")
    count = int(rate * duration)
    for frequency in notes:
        for n in range(count):
            t = n / rate
            envelope = min(1, n / (rate * 0.012)) * max(0, 1 - n / count) ** 1.7
            tone = math.sin(math.tau * frequency * t) + 0.22 * math.sin(math.tau * frequency * 2 * t)
            samples.extend([int(5500 * envelope * tone)] * channels)
    return pygame.mixer.Sound(buffer=samples.tobytes())
