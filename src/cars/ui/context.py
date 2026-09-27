"""Services shared by every screen: the window, the interface toolkit, audio and pointer."""

from typing import TYPE_CHECKING

import pygame

from cars.ui.kit.ui import Ui, default_scale

if TYPE_CHECKING:
    from cars.ui.audio import Audio

AUTO = 0  # The UI-scale setting that follows the window size.


class UiContext:
    def __init__(self, screen: pygame.Surface, audio: "Audio | None" = None) -> None:
        self.ui = Ui(screen)
        self.ui.mouse = self.mouse_pos
        self.audio = audio
        # Pointer override for tests and replays; None uses the OS cursor.
        self.pointer: tuple[int, int] | None = None
        self.borderless = False
        self.display_toggle_requested = False
        self.fit_scale()

    @property
    def screen(self) -> pygame.Surface:
        return self.ui.surface

    def set_surface(self, surface: pygame.Surface) -> None:
        """Follow a resized or recreated window."""
        self.ui.surface = surface
        self.ui.cache.clear()
        self.fit_scale()

    @property
    def scale_setting(self) -> float:
        return self.audio.settings.get("ui_scale", AUTO) if self.audio else AUTO

    def fit_scale(self) -> None:
        """Apply the player's UI scale, or the one that suits the window."""
        scale = self.scale_setting or default_scale(self.ui.surface.get_height())
        if scale != self.ui.scale:
            self.ui.set_scale(scale)

    def mouse_pos(self) -> tuple[int, int]:
        return self.pointer if self.pointer is not None else pygame.mouse.get_pos()

    def request_display_toggle(self) -> None:
        self.display_toggle_requested = True

    def play(self, sound: str) -> None:
        if self.audio:
            self.audio.play(sound)
