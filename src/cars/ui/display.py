"""The game window. Everything draws on a fixed canvas that is scaled to fit the window."""

import pygame

from cars.ui.palette import CANVAS_SIZE

OFF_CANVAS = (-100, -100)
LETTERBOX = (15, 19, 24)


class Display:
    def __init__(self, borderless: bool = False) -> None:
        self.canvas = pygame.Surface(CANVAS_SIZE)
        self.borderless = borderless
        self.open()

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
            size = (min(CANVAS_SIZE[0], desktop[0] - 60), min(CANVAS_SIZE[1], desktop[1] - 90))
        self.window = pygame.display.set_mode(size, pygame.NOFRAME if self.borderless else pygame.RESIZABLE)
        if self.borderless:
            pygame.Window.from_display_module().position = (0, 0)
        self.viewport = self.canvas.get_rect().fit(self.window.get_rect())

    def resize(self) -> None:
        self.window = pygame.display.get_surface()
        self.viewport = self.canvas.get_rect().fit(self.window.get_rect())

    def toggle(self) -> None:
        self.borderless = not self.borderless
        self.open()

    def point(self, pos: tuple[int, int]) -> tuple[int, int]:
        """Convert a window position to canvas coordinates."""
        if not self.viewport.collidepoint(pos):
            return OFF_CANVAS
        return tuple(
            int((pos[i] - self.viewport.topleft[i]) * CANVAS_SIZE[i] / self.viewport.size[i]) for i in (0, 1)
        )

    def event(self, event: pygame.event.Event) -> pygame.event.Event:
        """Copy of ``event`` with mouse positions and motion in canvas coordinates."""
        data = event.dict.copy()
        if "pos" in data:
            data["pos"] = self.point(data["pos"])
        if "rel" in data:
            data["rel"] = tuple(data["rel"][i] * CANVAS_SIZE[i] / self.viewport.size[i] for i in (0, 1))
        return pygame.event.Event(event.type, data)

    def present(self) -> None:
        self.window.fill(LETTERBOX)
        self.window.blit(pygame.transform.smoothscale(self.canvas, self.viewport.size), self.viewport)
        pygame.display.flip()
