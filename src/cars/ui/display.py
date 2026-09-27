"""The game window. Screens draw straight onto it at its native resolution."""

import pygame

WINDOWED_LIMIT = (1600, 1000)
DESKTOP_MARGIN = (80, 100)


class Display:
    def __init__(self, borderless: bool = False) -> None:
        self.borderless = borderless
        self.open()

    @property
    def surface(self) -> pygame.Surface:
        return pygame.display.get_surface()

    def open(self) -> None:
        # SDL keeps a maximized window maximized across set_mode calls on Windows,
        # which clamps a borderless window to the work area. Restore it first.
        if pygame.display.get_surface() is not None:
            pygame.Window.from_display_module().restore()
            pygame.event.pump()
        desktop = pygame.display.get_desktop_sizes()[0]
        if self.borderless:
            size = desktop
        else:
            size = tuple(
                min(limit, available - margin)
                for limit, available, margin in zip(WINDOWED_LIMIT, desktop, DESKTOP_MARGIN, strict=True)
            )
        flags = pygame.NOFRAME if self.borderless else pygame.RESIZABLE
        pygame.display.set_mode(size, flags)
        if self.borderless:
            pygame.Window.from_display_module().position = (0, 0)

    def toggle(self) -> None:
        self.borderless = not self.borderless
        self.open()

    def present(self) -> None:
        pygame.display.flip()
