"""Services shared by every screen: the canvas, widget theme, audio and pointer."""

from typing import TYPE_CHECKING

import pygame

from cars.ui.theme import Theme

if TYPE_CHECKING:
    from cars.ui.audio import Audio


class UiContext:
    def __init__(self, screen: pygame.Surface, audio: "Audio | None" = None) -> None:
        self.screen = screen
        self.theme = Theme(screen)
        self.theme.mouse_pos = self.mouse_pos
        self.audio = audio
        # Canvas-space pointer, set by the app each frame; None falls back to the OS cursor.
        self.pointer: tuple[int, int] | None = None
        self.borderless = False
        self.display_toggle_requested = False

    def mouse_pos(self) -> tuple[int, int]:
        return self.pointer if self.pointer is not None else pygame.mouse.get_pos()

    def request_display_toggle(self) -> None:
        self.display_toggle_requested = True

    def play(self, sound: str) -> None:
        if self.audio:
            self.audio.play(sound)
