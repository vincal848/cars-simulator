"""The interface toolkit: text, panels, buttons and icons drawn at native resolution.

Every size a caller passes is in logical pixels, multiplied by the UI scale, so
the whole interface grows with the player's setting and stays sharp. Positions
and rectangles are physical pixels on the window; build them with :meth:`Ui.px`
and :meth:`Ui.rect`.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pygame

from cars.ui.art.badges import glyph
from cars.ui.kit import style
from cars.ui.kit.tooltips import Tooltips
from cars.ui.text import wrap
from cars.ui.typography import DEFAULT_FONT, system_font

Color = tuple[int, int, int]
SCALES = (1.0, 1.25, 1.5, 1.75, 2.0)


BASE_HEIGHT = 860  # The window height the interface is designed for at 100%.


def default_scale(window_height: int) -> float:
    """The UI scale that suits a window: 125% on a 1080-pixel screen, 150% at 1440, 200% at 2160."""
    for scale in reversed(SCALES):
        if window_height >= BASE_HEIGHT * scale:
            return scale
    return SCALES[0]


class Ui:
    def __init__(self, surface: pygame.Surface, scale: float = 1.0, font_index: int = DEFAULT_FONT) -> None:
        self.surface = surface
        self.scale = scale
        self.font_index = font_index
        self.mouse: Callable[[], tuple[int, int]] = pygame.mouse.get_pos
        self.tips = Tooltips()
        self.cache: dict = {}
        self._fonts: dict[tuple, pygame.font.Font] = {}

    # Scale ----------------------------------------------------------------------------

    def set_scale(self, scale: float) -> None:
        self.scale = scale
        self._fonts.clear()
        self.cache.clear()

    def set_font(self, index: int) -> None:
        self.font_index = index
        self._fonts.clear()
        self.cache.clear()

    def px(self, value: float) -> int:
        """A logical length in physical pixels."""
        return round(value * self.scale)

    def rect(self, x: float, y: float, width: float, height: float) -> pygame.Rect:
        """A rectangle given in logical pixels, in physical pixels."""
        return pygame.Rect(self.px(x), self.px(y), self.px(width), self.px(height))

    @property
    def screen(self) -> pygame.Rect:
        return self.surface.get_rect()

    def font(self, size: int = style.BODY, bold: bool = False, italic: bool = False) -> pygame.font.Font:
        key = (self.font_index, self.px(size), bold, italic)
        if key not in self._fonts:
            self._fonts[key] = system_font(self.font_index, self.px(size), italic=italic, bold=bold)
        return self._fonts[key]

    def hovered(self, rect: pygame.Rect) -> bool:
        return rect.collidepoint(self.mouse())

    # Text -----------------------------------------------------------------------------

    def text(
        self,
        text: object,
        position: tuple[float, float],
        size: int = style.BODY,
        color: Color = style.INK,
        width: int | None = None,
        align: str = "left",
        bold: bool = False,
        italic: bool = False,
    ) -> pygame.Rect:
        """One line of text; ``width`` trims it with an ellipsis, ``align`` is relative to x."""
        font = self.font(size, bold, italic)
        text = str(text)
        if width is not None:
            text = self.fit(text, font, width)
        label = font.render(text, True, color)
        x, y = position
        if align == "center":
            x -= label.get_width() / 2
        elif align == "right":
            x -= label.get_width()
        return self.surface.blit(label, (round(x), round(y)))

    def centered(
        self,
        text: object,
        rect: pygame.Rect,
        size: int = style.BODY,
        color: Color = style.INK,
        bold: bool = False,
    ) -> None:
        font = self.font(size, bold)
        label = font.render(self.fit(str(text), font, rect.width - self.px(6)), True, color)
        self.surface.blit(label, label.get_rect(center=rect.center))

    @staticmethod
    def fit(text: str, font: pygame.font.Font, width: int) -> str:
        if font.size(text)[0] <= width:
            return text
        while len(text) > 1 and font.size(text + "…")[0] > width:
            text = text[:-1]
        return text.rstrip() + "…"

    def paragraph(
        self,
        text: str,
        rect: pygame.Rect,
        size: int = style.BODY,
        color: Color = style.INK,
        spacing: float = 1.35,
    ) -> int:
        """Wrapped text inside ``rect``; returns the height it took (lines past the bottom are dropped)."""
        font = self.font(size)
        line_height = round(font.get_height() * spacing)
        y = rect.y
        for line in wrap(text, font, rect.width):
            if y + font.get_height() > rect.bottom:
                break
            self.surface.blit(font.render(line, True, color), (rect.x, y))
            y += line_height
        return y - rect.y

    def paragraph_height(self, text: str, width: int, size: int = style.BODY, spacing: float = 1.35) -> int:
        font = self.font(size)
        return len(wrap(text, font, width)) * round(font.get_height() * spacing)

    # Surfaces -------------------------------------------------------------------------

    def panel(self, rect: pygame.Rect, title: str | None = None, icon: str | None = None) -> pygame.Rect:
        """A parchment panel with a brass frame and an optional slate title bar.

        Returns the area inside, below the title bar and inside the padding.
        """
        self.shadow(rect)
        pygame.draw.rect(self.surface, style.PARCHMENT, rect)
        inner = rect.inflate(-self.px(style.PAD) * 2, -self.px(style.PAD) * 2)
        if title is not None:
            header = pygame.Rect(rect.x, rect.y, rect.width, self.px(40))
            self.header(header, title, icon)
            inner.top = header.bottom + self.px(style.PAD)
            inner.height = rect.bottom - inner.top - self.px(style.PAD)
        self.frame(rect)
        return inner

    def header(self, rect: pygame.Rect, title: str, icon: str | None = None) -> None:
        pygame.draw.rect(self.surface, style.SLATE, rect)
        pygame.draw.line(
            self.surface, style.BRASS, rect.bottomleft, (rect.right - 1, rect.bottom - 1), self.px(2)
        )
        x = rect.x + self.px(style.PAD)
        if icon:
            size = self.px(22)
            self.icon(icon, (x + size // 2, rect.centery), 22, style.BRASS_LIGHT)
            x += size + self.px(8)
        font = self.font(style.HEADING, bold=True)
        label = font.render(self.fit(title, font, rect.right - x - self.px(44)), True, style.ON_SLATE)
        self.surface.blit(label, label.get_rect(midleft=(x, rect.centery)))

    def frame(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.surface, style.FRAME, rect, max(1, self.px(1)))
        pygame.draw.rect(self.surface, style.BRASS, rect.inflate(-self.px(2) * 2, -self.px(2) * 2), 1)

    def bar(self, rect: pygame.Rect) -> None:
        """A slate strip, such as the top bar, with a brass edge on the map side."""
        pygame.draw.rect(self.surface, style.SLATE, rect)
        width = max(1, self.px(2))
        if rect.top == 0:
            pygame.draw.line(
                self.surface,
                style.BRASS,
                (rect.x, rect.bottom - width),
                (rect.right, rect.bottom - width),
                width,
            )
        else:
            pygame.draw.line(self.surface, style.BRASS, rect.topleft, rect.topright, width)

    def inset(self, rect: pygame.Rect, color: Color = style.PARCHMENT_LIGHT) -> None:
        pygame.draw.rect(self.surface, color, rect, border_radius=self.px(3))
        pygame.draw.rect(self.surface, style.RULE, rect, 1, border_radius=self.px(3))

    def rule(self, x1: int, x2: int, y: int, color: Color = style.RULE) -> None:
        pygame.draw.line(self.surface, color, (x1, y), (x2, y), max(1, self.px(1)))

    def shadow(self, rect: pygame.Rect, depth: float = 6) -> None:
        key = ("shadow", rect.size, depth)
        if key not in self.cache:
            spread = self.px(depth)
            shade = pygame.Surface((rect.width + spread * 2, rect.height + spread * 2), pygame.SRCALPHA)
            for step in range(spread):
                alpha = int(60 * (step + 1) / spread)
                pygame.draw.rect(
                    shade,
                    (*style.SHADOW, alpha),
                    shade.get_rect().inflate(-step * 2, -step * 2),
                    1,
                    border_radius=spread,
                )
            pygame.draw.rect(shade, (*style.SHADOW, 60), shade.get_rect().inflate(-spread * 2, -spread * 2))
            self.cache[key] = shade
        spread = self.px(depth)
        self.surface.blit(self.cache[key], (rect.x - spread + self.px(2), rect.y - spread + self.px(3)))

    def veil(self, color=style.VEIL) -> None:
        key = ("veil", self.surface.get_size(), color)
        if key not in self.cache:
            shade = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
            shade.fill(color)
            self.cache[key] = shade
        self.surface.blit(self.cache[key], (0, 0))

    @contextmanager
    def clip(self, rect: pygame.Rect) -> Iterator[None]:
        previous = self.surface.get_clip()
        self.surface.set_clip(rect.clip(previous) if previous else rect)
        try:
            yield
        finally:
            self.surface.set_clip(previous)

    # Controls -------------------------------------------------------------------------

    def button(
        self,
        rect: pygame.Rect,
        label: str,
        kind: str = "secondary",
        selected: bool = False,
        enabled: bool = True,
        icon: str | None = None,
    ) -> None:
        """``kind`` is "primary" (slate, for the main action), "secondary" or "ghost"."""
        hovered = enabled and self.hovered(rect)
        radius = self.px(3)
        if kind == "primary":
            fill = style.SLATE_LIGHT if hovered else style.SLATE
            ink = style.ON_SLATE if enabled else style.ON_SLATE_MUTED
        elif kind == "ghost":
            fill = style.HOVER_ROW if hovered or selected else None
            ink = style.INK if enabled else style.INK_FAINT
        else:
            fill = (
                style.SELECTED_ROW if selected else style.PARCHMENT_DARK if hovered else style.PARCHMENT_LIGHT
            )
            ink = style.INK if enabled else style.INK_FAINT
        if not enabled and kind != "primary":
            fill = style.PARCHMENT
        if fill:
            pygame.draw.rect(self.surface, fill, rect, border_radius=radius)
        if kind != "ghost":
            edge = style.HIGHLIGHT if selected else style.SLATE_DARK if kind == "primary" else style.RULE
            pygame.draw.rect(self.surface, edge, rect, max(1, self.px(1)), border_radius=radius)
        font = self.font(style.BODY, bold=kind == "primary")
        size = self.px(18) if icon else 0
        gap = self.px(6) if icon else 0
        text = self.fit(label, font, rect.width - size - gap - self.px(12))
        width = size + gap + font.size(text)[0]
        x = rect.centerx - width // 2
        if icon:
            self.icon(icon, (x + size // 2, rect.centery), 18, ink)
        rendered = font.render(text, True, ink)
        self.surface.blit(rendered, rendered.get_rect(midleft=(x + size + gap, rect.centery)))

    def icon_button(
        self,
        rect: pygame.Rect,
        icon: str,
        selected: bool = False,
        on_slate: bool = True,
        badge: str | None = None,
    ) -> None:
        """A square icon button, as in the side bar and map-mode bar."""
        hovered = self.hovered(rect)
        if selected:
            pygame.draw.rect(
                self.surface,
                style.HIGHLIGHT if on_slate else style.SELECTED_ROW,
                rect,
                border_radius=self.px(4),
            )
        elif hovered:
            pygame.draw.rect(
                self.surface,
                style.SLATE_LIGHT if on_slate else style.HOVER_ROW,
                rect,
                border_radius=self.px(4),
            )
        color = style.SLATE_DARK if selected and on_slate else style.ON_SLATE if on_slate else style.INK
        self.icon(icon, rect.center, round(rect.height / self.scale * 0.62), color)
        if badge:
            font = self.font(style.SMALL, bold=True)
            label = font.render(badge, True, style.ON_SLATE)
            box = label.get_rect(bottomright=(rect.right + self.px(2), rect.bottom + self.px(2))).inflate(
                self.px(6), 0
            )
            pygame.draw.rect(self.surface, style.SLATE_DARK, box, border_radius=self.px(6))
            self.surface.blit(label, label.get_rect(center=box.center))

    def icon(self, kind: str, center: tuple[float, float], size: float, color: Color = style.INK) -> None:
        image = glyph(kind, self.px(size), tuple(color))
        self.surface.blit(image, image.get_rect(center=(round(center[0]), round(center[1]))))

    def close_button(self, header: pygame.Rect) -> pygame.Rect:
        """The close cross at the right end of a panel's title bar; returns its rectangle."""
        size = self.px(28)
        rect = pygame.Rect(header.right - size - self.px(6), header.centery - size // 2, size, size)
        if self.hovered(rect):
            pygame.draw.rect(self.surface, style.SLATE_LIGHT, rect, border_radius=self.px(3))
        inset = self.px(9)
        width = max(2, self.px(2))
        pygame.draw.line(
            self.surface,
            style.ON_SLATE,
            (rect.x + inset, rect.y + inset),
            (rect.right - inset, rect.bottom - inset),
            width,
        )
        pygame.draw.line(
            self.surface,
            style.ON_SLATE,
            (rect.x + inset, rect.bottom - inset),
            (rect.right - inset, rect.y + inset),
            width,
        )
        return rect

    def disclosure(self, center: tuple[int, int], open_: bool, color: Color = style.ON_SLATE) -> None:
        """A small triangle: pointing down when a section is open, right when folded."""
        x, y = center
        size = self.px(5)
        if open_:
            points = [(x - size, y - size // 2), (x + size, y - size // 2), (x, y + size)]
        else:
            points = [(x - size // 2, y - size), (x - size // 2, y + size), (x + size, y)]
        pygame.draw.polygon(self.surface, color, points)

    def progress(self, rect: pygame.Rect, fraction: float, color: Color = style.HIGHLIGHT) -> None:
        pygame.draw.rect(self.surface, style.PARCHMENT_DARK, rect, border_radius=rect.height // 2)
        filled = rect.copy()
        filled.width = round(rect.width * max(0.0, min(1.0, fraction)))
        if filled.width:
            pygame.draw.rect(self.surface, color, filled, border_radius=rect.height // 2)

    def swatch(self, center: tuple[int, int], color: Color, radius: float = 7) -> None:
        """A small disc in a nation's colour."""
        pygame.draw.circle(self.surface, color, center, self.px(radius))
        pygame.draw.circle(self.surface, style.FRAME, center, self.px(radius), max(1, self.px(1)))

    def hint(self, rect: pygame.Rect, title: str, body: str) -> None:
        self.tips.add(rect, title, body, self.mouse())
