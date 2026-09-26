"""Sound and preferences, and the music collection browser."""

import pygame

from cars.ui.audio import VOLUMES
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import DIM, GOLD

TRACKS_PER_PAGE = 3
VOLUME_STEP = 0.1


class SettingsDialog(Dialog):
    title = "Sound & Preferences"
    seal = "settings"

    def layout(self) -> dict[str, pygame.Rect]:
        buttons = {"collection": pygame.Rect(280, 511, 605, 36)}
        for i, key in enumerate(VOLUMES):
            for side, x in (("-", 727), ("+", 835)):
                buttons[key + side] = pygame.Rect(x, 230 + i * 70, 40, 32)
        buttons["autosave"] = pygame.Rect(620, 451, 265, 36)
        return buttons

    def click(self, action: str) -> None:
        if action == "collection":
            self.game.dialogs.open("music")
            return
        audio = self.game.context.audio
        if audio:
            key = "autosave" if action == "autosave" else action[:-1]
            audio.change(key, VOLUME_STEP if action.endswith("+") else -VOLUME_STEP)
            audio.play("click")

    def draw(self) -> None:
        t = self.theme
        audio = self.game.context.audio
        values = audio.settings if audio else dict(master=0, effects=0, music=0, autosave=False)
        for i, key in enumerate(VOLUMES):
            y = 230 + i * 70
            t.text(key.title() + " volume", 280, y, t.heading)
            t.text(f"{values[key]:.0%}", 784, y + 5, t.body)
            t.button(self.buttons[key + "-"], "-")
            t.button(self.buttons[key + "+"], "+")
        t.text("End-turn autosave", 280, 459, t.heading)
        t.button(self.buttons["autosave"], "Enabled" if values["autosave"] else "Disabled")
        t.button(self.buttons["collection"], "Music Collection / Choose a recording")
        footer = "Classical recordings cycle automatically. Effects and music have separate volume."
        if audio and audio.error:
            footer = audio.error
        t.text(footer, 280, 568, t.body, DIM, width=628)


class MusicDialog(Dialog):
    title = "The Music Collection"
    seal = "end"

    def layout(self) -> dict[str, pygame.Rect]:
        buttons = {f"track{i}": pygame.Rect(268, 225 + i * 77, 664, 69) for i in range(TRACKS_PER_PAGE)}
        for i, name in enumerate(("previous", "pause", "next", "shuffle")):
            buttons[name] = pygame.Rect(268 + i * 170, 470, 154, 34)
        buttons.update(
            page_previous=pygame.Rect(778, 183, 72, 28),
            page_next=pygame.Rect(860, 183, 72, 28),
            music_minus=pygame.Rect(780, 612, 52, 30),
            music_plus=pygame.Rect(880, 612, 52, 30),
        )
        return buttons

    def _last_page(self, count: int) -> int:
        return (count - 1) // TRACKS_PER_PAGE

    def click(self, action: str) -> None:
        audio = self.game.context.audio
        if not audio:
            return
        if action == "page_previous":
            self.page = max(0, self.page - 1)
        elif action == "page_next":
            self.page = min(self._last_page(len(audio.tracks)), self.page + 1)
        elif action.startswith("track"):
            audio.select(self.page * TRACKS_PER_PAGE + int(action[-1]))
        elif action == "previous":
            audio.skip(-1)
        elif action == "next":
            audio.skip(1)
        elif action == "pause":
            audio.toggle_pause()
        elif action == "shuffle":
            audio.change("shuffle")
        elif action in ("music_minus", "music_plus"):
            audio.change("music", VOLUME_STEP if action == "music_plus" else -VOLUME_STEP)

    def draw(self) -> None:
        t = self.theme
        audio = self.game.context.audio
        if not audio:
            t.text("Audio is unavailable.", 268, 200, t.body)
            return
        self.page = max(0, min(self.page, max(0, self._last_page(len(audio.tracks)))))
        t.text(f"CLASSICAL COLLECTION / {len(audio.tracks)} recordings", 268, 188, t.small, GOLD)
        t.button(self.buttons["page_previous"], "<")
        t.button(self.buttons["page_next"], ">")
        first = self.page * TRACKS_PER_PAGE
        for i, track in enumerate(audio.tracks[first : first + TRACKS_PER_PAGE]):
            rect = self.buttons[f"track{i}"]
            active = first + i == audio.index
            t.panel(rect, active)
            t.seal("end", (rect.x + 27, rect.y + 31), 32)
            t.text(track["title"], rect.x + 54, rect.y + 10, t.heading, GOLD if active else DIM, width=590)
            t.text(track["performer"], rect.x + 54, rect.y + 37, t.small, DIM, width=516)
            seconds = int(track.get("duration", 0))
            t.text(f"{seconds // 60}:{seconds % 60:02}", rect.right - 57, rect.y + 37, t.small, DIM)
            t.hint(
                rect,
                track["title"],
                track["license"]
                + " / "
                + track["performer"]
                + "\nClick to play. Full provenance is bundled in MUSIC_CREDITS.md.",
            )
        settings = audio.settings
        labels = (
            ("previous", "Previous"),
            ("pause", "Resume" if settings["paused"] else "Pause"),
            ("next", "Next"),
            ("shuffle", "Shuffle: on" if settings["shuffle"] else "Shuffle: off"),
        )
        for name, label in labels:
            t.button(self.buttons[name], label)
        if not audio.available:
            status = "Audio unavailable"
        elif not audio.music_loaded:
            status = "Music unavailable"
        else:
            status = "Paused" if settings["paused"] else "Now playing"
        t.text(status, 268, 521, t.small, GOLD)
        current = audio.current
        t.text(current["title"] if current else "No recordings installed", 268, 547, t.heading, width=660)
        detail = audio.error or ((current["license"] + " / Automatic collection cycling") if current else "")
        t.text(detail, 268, 578, t.small, DIM, width=660)
        t.text("Music volume (master volume also applies)", 268, 617, t.body, width=500)
        t.button(self.buttons["music_minus"], "-")
        t.button(self.buttons["music_plus"], "+")
        t.text(f"{settings['music']:.0%}", 840, 619, t.small)
