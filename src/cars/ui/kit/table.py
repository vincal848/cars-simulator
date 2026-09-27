"""Sortable, scrollable tables: the backbone of every list in the interface."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import pygame

from cars.ui.kit import style
from cars.ui.kit.ui import Ui


@dataclass
class Column:
    title: str
    value: Callable[[Any], object]  # the cell's content, also used to sort unless ``sort`` is given
    width: float | None = None  # logical pixels; None shares the remaining width
    align: str = "left"
    sort: Callable[[Any], object] | None = None
    draw: Callable[[Ui, pygame.Rect, Any], None] | None = None  # custom cell painter
    color: Callable[[Any], tuple[int, int, int]] | None = None
    hint: str = ""


class Table:
    def __init__(
        self, columns: Sequence[Column], row_height: float = style.ROW, sort: int | None = None
    ) -> None:
        self.columns = list(columns)
        self.row_height = row_height
        self.sort_column = sort
        self.descending = False
        self.scroll = 0
        self.rows: list = []
        self._rect: pygame.Rect | None = None
        self._header: dict[int, pygame.Rect] = {}
        self._row_rects: list[tuple[pygame.Rect, Any]] = []

    def sorted(self, rows: Sequence) -> list:
        if self.sort_column is None:
            return list(rows)
        column = self.columns[self.sort_column]
        key = column.sort or column.value
        return sorted(rows, key=lambda row: _sortable(key(row)), reverse=self.descending)

    def draw(self, ui: Ui, rect: pygame.Rect, rows: Sequence, selected: Any = None) -> None:
        self._rect = rect
        self.rows = self.sorted(rows)
        widths = self._widths(ui, rect.width)
        header = pygame.Rect(rect.x, rect.y, rect.width, ui.px(self.row_height))
        pygame.draw.rect(ui.surface, style.PANEL_DARK, header)
        ui.rule(header.x, header.right, header.bottom - 1, style.ACCENT)
        self._header = {}
        x = rect.x
        for index, (column, width) in enumerate(zip(self.columns, widths, strict=True)):
            cell = pygame.Rect(x, header.y, width, header.height)
            self._header[index] = cell
            self._cell_text(ui, cell, column.title, column.align, style.INK_MUTED, bold=True)
            if index == self.sort_column:
                self._sort_marker(ui, cell, column)
            if column.hint:
                ui.hint(cell, column.title, column.hint)
            x += width
        body = pygame.Rect(rect.x, header.bottom, rect.width, rect.bottom - header.bottom)
        row_height = ui.px(self.row_height)
        self.scroll = max(0, min(self.scroll, len(self.rows) * row_height - body.height))
        self._row_rects = []
        with ui.clip(body):
            for number, row in enumerate(self.rows):
                top = body.y + number * row_height - self.scroll
                if top + row_height < body.y or top > body.bottom:
                    continue
                line = pygame.Rect(rect.x, top, rect.width, row_height)
                self._row_rects.append((line, row))
                fill = style.PANEL_LIGHT if number % 2 == 0 else style.PANEL
                if row is selected:
                    fill = style.SELECTED_ROW
                elif ui.hovered(line) and body.collidepoint(ui.mouse()):
                    fill = style.HOVER_ROW
                pygame.draw.rect(ui.surface, fill, line)
                x = rect.x
                for column, width in zip(self.columns, widths, strict=True):
                    cell = pygame.Rect(x, top, width, row_height)
                    if column.draw:
                        column.draw(ui, cell, row)
                    else:
                        color = column.color(row) if column.color else style.INK
                        self._cell_text(ui, cell, _format(column.value(row)), column.align, color)
                    x += width
        if len(self.rows) * row_height > body.height:
            self._scrollbar(ui, body, len(self.rows) * row_height)
        if not self.rows:
            ui.text(
                "Nothing to show.",
                (body.x + ui.px(style.PAD), body.y + ui.px(8)),
                style.BODY,
                style.INK_FAINT,
            )

    def handle(self, event: pygame.event.Event, ui: Ui) -> tuple[str, Any] | None:
        """("sort", column index) after a header click, ("row", row) after a row click, else None."""
        if self._rect is None:
            return None
        if event.type == pygame.MOUSEWHEEL and self._rect.collidepoint(ui.mouse()):
            self.scroll -= event.y * ui.px(self.row_height) * 3
            return ("scroll", None)
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        for index, cell in self._header.items():
            if cell.collidepoint(event.pos):
                if self.sort_column == index:
                    self.descending = not self.descending
                else:
                    self.sort_column, self.descending = index, False
                return ("sort", index)
        for line, row in self._row_rects:
            if line.collidepoint(event.pos) and self._rect.collidepoint(event.pos):
                return ("row", row)
        return None

    def _widths(self, ui: Ui, total: int) -> list[int]:
        fixed = sum(ui.px(c.width) for c in self.columns if c.width is not None)
        flexible = [c for c in self.columns if c.width is None]
        share = max(0, total - fixed) // max(1, len(flexible))
        widths = [ui.px(c.width) if c.width is not None else share for c in self.columns]
        widths[-1] += total - sum(widths)
        return widths

    def _sort_marker(self, ui: Ui, cell: pygame.Rect, column: Column) -> None:
        """A small triangle beside the sorted column's title: up ascending, down descending."""
        font = ui.font(style.BODY, bold=True)
        width = font.size(column.title)[0]
        pad = ui.px(8)
        if column.align == "right":
            x = cell.right - pad - width - ui.px(10)
        else:
            x = cell.x + pad + width + ui.px(10)
        y, size = cell.centery, ui.px(4)
        if self.descending:
            points = [(x - size, y - size // 2), (x + size, y - size // 2), (x, y + size)]
        else:
            points = [(x - size, y + size // 2), (x + size, y + size // 2), (x, y - size)]
        pygame.draw.polygon(ui.surface, style.SLATE, points)

    @staticmethod
    def _cell_text(ui: Ui, cell: pygame.Rect, text: str, align: str, color, bold: bool = False) -> None:
        pad = ui.px(8)
        font = ui.font(style.BODY, bold=bold)
        text = ui.fit(text, font, cell.width - pad * 2)
        label = font.render(text, True, color)
        if align == "right":
            spot = label.get_rect(midright=(cell.right - pad, cell.centery))
        elif align == "center":
            spot = label.get_rect(center=cell.center)
        else:
            spot = label.get_rect(midleft=(cell.x + pad, cell.centery))
        ui.surface.blit(label, spot)

    def _scrollbar(self, ui: Ui, body: pygame.Rect, content: int) -> None:
        track = pygame.Rect(body.right - ui.px(5), body.y, ui.px(4), body.height)
        thumb = track.copy()
        thumb.height = max(ui.px(20), round(body.height * body.height / content))
        thumb.y = body.y + round((body.height - thumb.height) * self.scroll / max(1, content - body.height))
        pygame.draw.rect(ui.surface, style.PANEL_DARK, track, border_radius=track.width // 2)
        pygame.draw.rect(ui.surface, style.ACCENT, thumb, border_radius=track.width // 2)


def _format(value: object) -> str:
    if isinstance(value, float):
        return f"{value:,.1f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _sortable(value: object) -> tuple:
    """Numbers sort as numbers and text as text, numbers first."""
    if isinstance(value, (int, float)):
        return (0, value, "")
    return (1, 0, str(value).lower())
