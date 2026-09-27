"""The atlas-and-brass widget kit: panels, buttons, text and seals drawn on one screen."""

import random
from collections.abc import Callable

import pygame

from cars.ui.art.badges import badge
from cars.ui.art.ornament import fleur
from cars.ui.palette import DIM, GOLD, PAPER, WELL
from cars.ui.text import wrap
from cars.ui.tooltips import Tooltips
from cars.ui.typography import DEFAULT_FONT, system_font

PANEL_DARK = (35, 23, 29)
PANEL_LIGHT = (78, 26, 37)
BUTTON = (38, 29, 33)
BUTTON_HOVER = (73, 39, 42)
BUTTON_PRIMARY = (122, 35, 47)


class Theme:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.mouse_pos: Callable[[], tuple[int, int]] = pygame.mouse.get_pos
        self.cache: dict = {}
        self.tips = Tooltips()
        self._fonts: dict[tuple[int, int], pygame.font.Font] = {}
        self.set_font(DEFAULT_FONT)

    # Typography -----------------------------------------------------------------------

    def set_font(self, index: int) -> None:
        self.font_index = index
        self.serif = self.font(23)
        self.heading = self.font(18)
        self.number = self.font(29)
        self.body = self.font(15)
        self.small = self.font(13)

    def font(self, size: int) -> pygame.font.Font:
        """The current face at ``size``, loaded once per theme."""
        key = (self.font_index, size)
        if key not in self._fonts:
            self._fonts[key] = system_font(self.font_index, size)
        return self._fonts[key]

    def text(self, text, x: float, y: float, font=None, color=PAPER, width: int | None = None) -> None:
        """Draw one line, trimmed with an ellipsis to ``width`` if given."""
        font = font or self.body
        text = str(text).replace(r"\cdot", " / ").replace("·", " / ")
        if width:
            while font.size(text)[0] > width and len(text) > 1:
                text = text[:-2].rstrip() + "…"
        self.screen.blit(font.render(text, True, color), (x, y))

    def centered(self, text: str, center_x: float, y: float, font, color=PAPER) -> None:
        label = font.render(text, True, color)
        self.screen.blit(label, label.get_rect(midtop=(center_x, y)))

    def paragraph(self, text: str, x: int, y: int, width: int, limit: int = 20, color=None) -> int:
        """Wrapped body text; returns the total number of lines."""
        lines = wrap(text, self.body, width)
        for i, line in enumerate(lines[:limit]):
            self.text(line, x, y + i * 23, self.body, color or PAPER)
        return len(lines)

    # Panels ---------------------------------------------------------------------------

    def panel(self, rect, light: bool = False) -> None:
        """A lacquered panel with a gilt edge; large panels get corner brackets."""
        rect = pygame.Rect(rect)
        key = (rect.size, light)
        if key not in self.cache:
            self.cache[key] = self._panel_surface(rect.size, light)
        screen = self.screen
        screen.blit(self.cache[key], rect)
        pygame.draw.rect(screen, (26, 15, 18), rect, 3, border_radius=4)
        pygame.draw.rect(screen, (149, 111, 61), rect.inflate(-2, -2), 1, border_radius=3)
        pygame.draw.line(screen, (230, 197, 128), (rect.x + 5, rect.y + 1), (rect.right - 5, rect.y + 1))
        pygame.draw.line(
            screen, (80, 49, 33), (rect.x + 4, rect.bottom - 2), (rect.right - 4, rect.bottom - 2)
        )
        if _is_large(rect.size):
            pygame.draw.rect(screen, (98, 68, 46), rect.inflate(-12, -12), 1, border_radius=3)
            corners = [
                (rect.x + 6, rect.y + 6, 1, 1),
                (rect.right - 7, rect.y + 6, -1, 1),
                (rect.x + 6, rect.bottom - 7, 1, -1),
                (rect.right - 7, rect.bottom - 7, -1, -1),
            ]
            for cx, cy, sx, sy in corners:
                pygame.draw.lines(screen, GOLD, False, [(cx, cy + sy * 16), (cx, cy), (cx + sx * 16, cy)], 1)
                pygame.draw.circle(screen, (229, 196, 126), (cx, cy), 2)

    @staticmethod
    def _panel_surface(size: tuple[int, int], light: bool) -> pygame.Surface:
        """Lacquer with a fine grain, lit from above and darkening towards the edges."""
        width, height = size
        surface = pygame.Surface(size)
        base = PANEL_LIGHT if light else PANEL_DARK
        for y in range(height):
            shade = int(8 * (1 - y / max(1, height)))
            pygame.draw.line(surface, tuple(c + shade for c in base), (0, y), (width, y))
        rng = random.Random(9)
        for _ in range(width * height // 9):
            x, y = rng.randrange(width), rng.randrange(height)
            color = surface.get_at((x, y))
            step = rng.choice((-5, -3, 3))
            surface.set_at((x, y), tuple(min(255, max(0, v + step)) for v in color[:3]))
        vignette = pygame.Surface(size, pygame.SRCALPHA)
        for inset in range(0, min(12, width // 4, height // 4)):
            pygame.draw.rect(
                vignette, (0, 0, 0, 14 - inset), (inset, inset, width - 2 * inset, height - 2 * inset), 1
            )
        surface.blit(vignette, (0, 0))
        return surface

    def bar(self, rect) -> None:
        """A full-width lacquered strip with a gilt lower edge, e.g. the top bar."""
        rect = pygame.Rect(rect)
        key = ("bar", rect.size)
        if key not in self.cache:
            self.cache[key] = self._panel_surface(rect.size, False)
        screen = self.screen
        shade = pygame.Surface((rect.width, 6), pygame.SRCALPHA)
        for i in range(6):
            pygame.draw.line(shade, (0, 0, 0, 90 - i * 15), (0, i), (rect.width, i))
        screen.blit(shade, (rect.x, rect.bottom))
        screen.blit(self.cache[key], rect)
        pygame.draw.line(screen, (230, 197, 128), (rect.x, rect.bottom - 3), (rect.right, rect.bottom - 3))
        pygame.draw.line(screen, (149, 111, 61), (rect.x, rect.bottom - 2), (rect.right, rect.bottom - 2))
        pygame.draw.line(screen, (26, 15, 18), (rect.x, rect.bottom - 1), (rect.right, rect.bottom - 1))

    def shadow(self, rect: pygame.Rect, spread: int, offset: int, alpha: int) -> None:
        """Soft drop shadow behind a floating window."""
        shade = pygame.Surface((rect.width + spread, rect.height + spread), pygame.SRCALPHA)
        shade.fill((0, 0, 0, alpha))
        self.screen.blit(shade, (rect.x + offset, rect.y + offset))

    def dim_screen(self, color: tuple[int, int, int, int]) -> None:
        shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shade.fill(color)
        self.screen.blit(shade, (0, 0))

    def inset(self, rect) -> None:
        rect = pygame.Rect(rect)
        pygame.draw.rect(self.screen, WELL, rect, border_radius=3)
        pygame.draw.line(self.screen, (9, 12, 15), rect.topleft, (rect.right, rect.top), 2)
        pygame.draw.line(self.screen, (99, 64, 49), (rect.x, rect.bottom), (rect.right, rect.bottom))

    def rule(self, x: int, y: int, width: int, label: str | None = None) -> None:
        pygame.draw.line(self.screen, (104, 92, 67), (x, y), (x + width, y))
        mid = x + width / 2
        pygame.draw.polygon(self.screen, GOLD, [(mid - 4, y), (mid, y - 3), (mid + 4, y), (mid, y + 3)])
        if label:
            self.text(label, x, y - 21, self.small, GOLD)

    # Controls -------------------------------------------------------------------------

    def button(
        self, rect, label: str, active: bool = False, enabled: bool = True, primary: bool = False
    ) -> None:
        screen = self.screen
        hovered = rect.collidepoint(self.mouse_pos()) and enabled
        primary = primary or label.startswith("END TURN")
        if primary:
            fill = BUTTON_PRIMARY
        else:
            fill = BUTTON_HOVER if active or hovered else BUTTON
        pygame.draw.rect(screen, (12, 14, 17), rect.move(0, 2), border_radius=4)
        pygame.draw.rect(screen, fill, rect, border_radius=4)
        pygame.draw.rect(screen, GOLD if primary or active else (103, 77, 57), rect, 1, border_radius=4)
        if primary or hovered:
            pygame.draw.line(screen, (224, 188, 118), (rect.x + 5, rect.y + 2), (rect.right - 5, rect.y + 2))
        if active and not primary:
            pygame.draw.circle(screen, GOLD, (rect.centerx, rect.bottom - 5), 2)
        font = self.heading if primary else self.body
        color = PAPER if enabled else DIM
        self.text(
            label,
            rect.centerx - font.size(label)[0] / 2,
            rect.centery - font.get_height() / 2 - 1,
            font,
            color,
        )

    def emblem_button(self, rect, label: str, kind: str, active: bool = False, help_text: str = "") -> None:
        """A button led by an engraved seal, e.g. the map-layer switches."""
        self.button(rect, "", active, primary=kind == "end")
        size = min(27, rect.height - 4)
        self.seal(kind, (rect.x + size / 2 + 5, rect.centery), size)
        text_y = rect.centery - self.small.get_height() / 2 - 1
        self.text(label, rect.x + size + 10, text_y, self.small, width=rect.width - size - 14)
        if help_text:
            self.hint(rect, label, help_text)

    def hint(self, rect, title: str, body: str) -> None:
        self.tips.add(rect, title, body, self.mouse_pos())

    # Heraldry -------------------------------------------------------------------------

    def seal(self, kind: str, center: tuple[float, float], size: int = 28) -> None:
        icon = badge(kind, size)
        self.screen.blit(icon, icon.get_rect(center=center))

    def shield(self, x: int, y: int, color, scale: float = 1) -> None:
        outline = [(0, 0), (42, 0), (40, 34), (21, 47), (2, 34)]
        points = [(x + px * scale, y + py * scale) for px, py in outline]
        pygame.draw.polygon(self.screen, (9, 17, 24), [(a + 3, b + 3) for a, b in points])
        pygame.draw.polygon(self.screen, color, points)
        pygame.draw.polygon(self.screen, GOLD, points, 2)
        fleur(self.screen, (x + 21 * scale, y + 22 * scale), round(27 * scale))


def _is_large(size: tuple[int, int]) -> bool:
    return size[0] > 300 and size[1] > 150
