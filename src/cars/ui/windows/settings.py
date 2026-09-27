"""Settings (display, interface size, fonts, sound) and the music collection."""

import pygame

from cars.ui.audio import VOLUMES
from cars.ui.frames import Window
from cars.ui.kit import style
from cars.ui.kit.grid import section
from cars.ui.kit.ui import SCALES, default_scale
from cars.ui.typography import FONT_CHOICES

VOLUME_STEP = 0.1


class SettingsWindow(Window):
    name = "settings"
    title = "Settings"
    icon = "settings"
    fit_content = True
    size = (640, 620)

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        context = self.game.context
        audio = context.audio
        x, y, width = rect.x, rect.y, rect.width
        label_width = ui.px(170)
        y += section(ui, "Display", x, y, width)
        ui.text("Interface size", (x, y + ui.px(6)), style.BODY)
        current = context.scale_setting
        options = [(0, "Auto")] + [(scale, f"{scale:.0%}") for scale in SCALES]
        button_width = (width - label_width) // len(options) - ui.px(4)
        for i, (value, label) in enumerate(options):
            button = pygame.Rect(x + label_width + i * (button_width + ui.px(4)), y, button_width, ui.px(30))
            self.button(button, label, f"scale:{value}", selected=current == value)
        y += ui.px(40)
        ui.text("Window", (x, y + ui.px(6)), style.BODY)
        mode = "Fullscreen" if context.borderless else "Windowed"
        self.button(
            pygame.Rect(x + label_width, y, ui.px(220), ui.px(30)), f"{mode} · switch (F11)", "display"
        )
        y += ui.px(40)
        ui.text("Typeface", (x, y + ui.px(6)), style.BODY)
        font_width = (width - label_width) // len(FONT_CHOICES) - ui.px(4)
        for i, (name, _faces) in enumerate(FONT_CHOICES):
            button = pygame.Rect(x + label_width + i * (font_width + ui.px(4)), y, font_width, ui.px(30))
            self.button(button, name, f"font:{i}", selected=ui.font_index == i)
        y += ui.px(52)
        y += section(ui, "Sound", x, y, width)
        values = audio.settings if audio else dict(master=0, effects=0, music=0, autosave=False)
        for key in VOLUMES:
            ui.text(f"{key.title()} volume", (x, y + ui.px(6)), style.BODY)
            minus = pygame.Rect(x + label_width, y, ui.px(34), ui.px(30))
            self.button(minus, "−", f"volume:{key}:-")
            bar = pygame.Rect(minus.right + ui.px(10), y + ui.px(11), ui.px(220), ui.px(8))
            ui.progress(bar, values[key])
            plus = pygame.Rect(bar.right + ui.px(10), y, ui.px(34), ui.px(30))
            self.button(plus, "+", f"volume:{key}:+")
            ui.text(f"{values[key]:.0%}", (plus.right + ui.px(12), y + ui.px(6)), style.BODY, style.INK_MUTED)
            y += ui.px(38)
        self.button(pygame.Rect(x + label_width, y, ui.px(220), ui.px(30)), "Music collection…", "music")
        y += ui.px(52)
        y += section(ui, "Campaign", x, y, width)
        ui.text("Autosave each turn", (x, y + ui.px(6)), style.BODY)
        self.button(
            pygame.Rect(x + label_width, y, ui.px(120), ui.px(30)),
            "On" if values["autosave"] else "Off",
            "autosave",
            selected=values["autosave"],
        )
        y += ui.px(44)
        if audio and audio.error:
            y += ui.paragraph(audio.error, pygame.Rect(x, y, width, ui.px(60)), style.SMALL, style.WARN)
        return y - rect.y

    def act(self, action: str) -> None:
        context = self.game.context
        audio = context.audio
        verb, _, value = action.partition(":")
        if verb == "scale":
            scale = float(value)
            if audio:
                audio.set("ui_scale", scale)
            context.ui.set_scale(scale or default_scale(context.ui.screen.height))
            self.game.renderer.map.invalidate_labels()
        elif verb == "font":
            context.ui.set_font(int(value))
            if audio:
                audio.set("font", int(value))
            self.game.renderer.map.invalidate_labels()
        elif verb == "display":
            context.request_display_toggle()
        elif verb == "music":
            self.game.open_window("music")
        elif audio and verb == "volume":
            key, direction = value.split(":")
            audio.change(key, VOLUME_STEP if direction == "+" else -VOLUME_STEP)
            audio.play("click")
        elif audio and verb == "autosave":
            audio.change("autosave")


class MusicWindow(Window):
    name = "music"
    title = "Music collection"
    icon = "end"
    fit_content = True
    size = (640, 560)

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        audio = self.game.context.audio
        x, y, width = rect.x, rect.y, rect.width
        if not audio:
            ui.text("Audio is unavailable.", (x, y), style.BODY)
            return ui.px(30)
        settings = audio.settings
        current = audio.current
        status = (
            "Paused" if settings["paused"] else "Now playing" if audio.music_loaded else "Music unavailable"
        )
        ui.text(status.upper(), (x, y), style.SMALL, style.SLATE, bold=True)
        ui.text(
            current["title"] if current else "No recordings installed",
            (x, y + ui.px(18)),
            style.HEADING,
            bold=True,
            width=width,
        )
        ui.text(
            audio.error or (current["performer"] + " · " + current["license"] if current else ""),
            (x, y + ui.px(44)),
            style.SMALL,
            style.INK_MUTED,
            width=width,
        )
        y += ui.px(74)
        controls = (
            ("previous", "Previous"),
            ("pause", "Resume" if settings["paused"] else "Pause"),
            ("next", "Next"),
            ("shuffle", "Shuffle on" if settings["shuffle"] else "Shuffle off"),
        )
        button_width = width // len(controls) - ui.px(6)
        for i, (action, label) in enumerate(controls):
            self.button(
                pygame.Rect(x + i * (button_width + ui.px(6)), y, button_width, ui.px(32)),
                label,
                action,
                kind="primary" if action == "pause" else "secondary",
            )
        y += ui.px(48)
        y += section(ui, "Recordings", x, y, width)
        for index, track in enumerate(audio.tracks):
            row = pygame.Rect(x, y, width, ui.px(52))
            active = index == audio.index
            ui.inset(
                row,
                style.SELECTED_ROW
                if active
                else style.PARCHMENT_DARK
                if ui.hovered(row)
                else style.PARCHMENT_LIGHT,
            )
            ui.text(
                track["title"],
                (row.x + ui.px(12), row.y + ui.px(6)),
                style.BODY,
                style.INK,
                bold=active,
                width=row.width - ui.px(90),
            )
            ui.text(
                track["performer"],
                (row.x + ui.px(12), row.y + ui.px(28)),
                style.SMALL,
                style.INK_MUTED,
                width=row.width - ui.px(90),
            )
            seconds = int(track.get("duration", 0))
            ui.text(
                f"{seconds // 60}:{seconds % 60:02}",
                (row.right - ui.px(12), row.y + ui.px(16)),
                style.BODY,
                style.INK_MUTED,
                align="right",
            )
            self.clickable(row, f"track:{index}")
            ui.hint(row, track["title"], track["license"] + ". Full credits are in MUSIC_CREDITS.md.")
            y += row.height + ui.px(6)
        return y - rect.y

    def act(self, action: str) -> None:
        audio = self.game.context.audio
        if not audio:
            return
        verb, _, value = action.partition(":")
        if verb == "track":
            audio.select(int(value))
        elif verb == "previous":
            audio.skip(-1)
        elif verb == "next":
            audio.skip(1)
        elif verb == "pause":
            audio.toggle_pause()
        elif verb == "shuffle":
            audio.change("shuffle")
