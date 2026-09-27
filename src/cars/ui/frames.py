"""Framed panels and windows: the docked panels on the left and the modal windows.

A frame is drawn immediately each frame. While drawing, it registers the areas
that respond to clicks with :meth:`Frame.clickable`; input is then routed by
looking those areas up, so drawing and hit testing can never disagree. Content
taller than the frame scrolls with the mouse wheel.
"""

from typing import TYPE_CHECKING

import pygame

from cars.ui.kit import style

if TYPE_CHECKING:
    from cars.ui.kit.ui import Ui
    from cars.ui.screens.game import GameScreen

HEADER = 40
SCROLL_STEP = 48


class Frame:
    title = ""
    icon = "chronicle"
    closable = True
    # Logical size of a centred window; docked panels ignore it.
    size = (720, 560)
    # Shrink a window's height to its content once that is known.
    fit_content = False

    def __init__(self, game: "GameScreen") -> None:
        self.game = game
        self.rect: pygame.Rect | None = None
        self.body: pygame.Rect | None = None
        self.areas: list[tuple[pygame.Rect, str]] = []
        self.scroll = 0
        self.content_height = 0
        self.notice = ""

    @property
    def ui(self) -> "Ui":
        return self.game.context.ui

    @property
    def state(self):
        return self.game.state

    def heading(self) -> str:
        return self.title

    # Placement ------------------------------------------------------------------------

    def place(self, screen: pygame.Rect) -> pygame.Rect:
        """Where the frame sits; centred windows by default."""
        ui = self.ui
        width = min(ui.px(self.size[0]), screen.width - ui.px(24))
        height = min(ui.px(self.size[1]), screen.height - ui.px(24))
        if self.fit_content and self.content_height:
            height = min(height, self.content_height + ui.px(HEADER) + ui.px(28))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = screen.center
        return rect

    def contains(self, point) -> bool:
        return self.rect is not None and self.rect.collidepoint(point)

    # Life cycle -----------------------------------------------------------------------

    def on_open(self) -> None:
        self.scroll = 0
        self.notice = ""

    def close(self) -> None:
        self.game.close_frame(self)

    # Drawing --------------------------------------------------------------------------

    def draw(self) -> None:
        ui = self.ui
        self.rect = self.place(ui.screen)
        self.areas = []
        inner = ui.panel(self.rect, self.heading(), self.icon)
        if self.closable:
            header = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, ui.px(HEADER))
            self.areas.append((ui.close_button(header), "close"))
        self.body = inner
        # Clamp with what was drawn last time, so a scroll set from outside never shows a blank page.
        self.scroll = max(0, min(self.scroll, self.content_height - inner.height))
        with ui.clip(inner):
            used = self.draw_body(ui, inner.move(0, -self.scroll))
        self.content_height = used
        overflow = used - inner.height
        self.scroll = max(0, min(self.scroll, overflow))
        if overflow > 0:
            self._scrollbar(ui, inner, used)

    def draw_body(self, ui: "Ui", rect: pygame.Rect) -> int:
        """Draw the content inside ``rect`` (already shifted by the scroll); return its height."""
        return 0

    def clickable(self, rect: pygame.Rect, action: str) -> None:
        """Make ``rect`` send ``action`` when clicked, where it is visible."""
        visible = rect.clip(self.body) if self.body else rect
        if visible.width and visible.height:
            self.areas.append((visible, action))

    def button(self, rect: pygame.Rect, label: str, action: str, **options) -> None:
        self.ui.button(rect, label, **options)
        if options.get("enabled", True):
            self.clickable(rect, action)

    def area_of(self, action: str) -> pygame.Rect | None:
        """Where ``action`` was last drawn; used by tests to click it."""
        return next((rect for rect, name in self.areas if name == action), None)

    def _scrollbar(self, ui: "Ui", body: pygame.Rect, content: int) -> None:
        track = pygame.Rect(body.right + ui.px(4), body.y, ui.px(4), body.height)
        thumb = track.copy()
        thumb.height = max(ui.px(24), round(body.height * body.height / content))
        thumb.y = body.y + round((body.height - thumb.height) * self.scroll / max(1, content - body.height))
        pygame.draw.rect(ui.surface, style.PANEL_DARK, track, border_radius=track.width // 2)
        pygame.draw.rect(ui.surface, style.ACCENT, thumb, border_radius=track.width // 2)

    # Input ----------------------------------------------------------------------------

    def handle(self, event: pygame.event.Event) -> bool:
        """Handle an event aimed at this frame; returns True when it was consumed."""
        position = getattr(event, "pos", None)
        if event.type == pygame.MOUSEWHEEL:
            if not self.contains(self.ui.mouse()):
                return False
            self.scroll = max(0, self.scroll - event.y * self.ui.px(SCROLL_STEP))
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.closable:
            self.close()
            return True
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and position is not None:
            if not self.contains(position):
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = next(
                    (name for rect, name in reversed(self.areas) if rect.collidepoint(position)), None
                )
                if action == "close":
                    self.close()
                elif action:
                    self.act(action)
            return True
        return self.handle_other(event)

    def handle_other(self, event: pygame.event.Event) -> bool:
        """Keys and other events; frames that take typing override this."""
        return False

    def act(self, action: str) -> None:
        """Respond to a click on a registered area."""


class DockedPanel(Frame):
    """A tall panel docked beside the side bar, as for a province or the military."""

    width = 450

    def place(self, screen: pygame.Rect) -> pygame.Rect:
        ui = self.ui
        left = self.game.renderer.sidebar.rect.right
        top = self.game.renderer.top_bar.rect.bottom
        return pygame.Rect(left, top, ui.px(self.width), screen.bottom - top)


class Window(Frame):
    """A modal window centred over a veiled map."""

    def draw(self) -> None:
        self.ui.veil()
        super().draw()

    def handle(self, event: pygame.event.Event) -> bool:
        super().handle(event)
        return True  # Modal: nothing behind a window receives input.
