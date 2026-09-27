"""Small static tables inside panels: a header row and ruled rows, no scrolling or sorting.

A cell is text, a (text, colour) pair, or a callable that paints the cell's rectangle
(for buttons and icons).
"""

from collections.abc import Callable, Sequence

import pygame

from cars.ui.kit import style
from cars.ui.kit.ui import Ui

Cell = str | tuple[str, tuple[int, int, int]] | Callable[[pygame.Rect], None]
Column = tuple[str, float | None, str]  # (title, logical width or None to share the rest, align)


def draw_grid(
    ui: Ui,
    x: int,
    y: int,
    width: int,
    columns: Sequence[Column],
    rows: Sequence[Sequence[Cell]],
    row_height: float = style.ROW,
    hints: Sequence[tuple[str, str] | None] | None = None,
) -> int:
    """Draw the table at (x, y); returns its height. ``hints`` give each row a tooltip."""
    fixed = sum(ui.px(w) for _, w, _ in columns if w is not None)
    flexible = sum(1 for _, w, _ in columns if w is None)
    share = max(0, width - fixed) // max(1, flexible)
    widths = [ui.px(w) if w is not None else share for _, w, _ in columns]
    widths[-1] += width - sum(widths)
    height = ui.px(row_height)
    header = pygame.Rect(x, y, width, ui.px(row_height - 4))
    pygame.draw.rect(ui.surface, style.PARCHMENT_DARK, header)
    ui.rule(header.x, header.right, header.bottom - 1, style.BRASS)
    left = x
    for (title, _, align), column_width in zip(columns, widths, strict=True):
        _cell(
            ui, pygame.Rect(left, header.y, column_width, header.height), title, align, style.INK_MUTED, True
        )
        left += column_width
    top = header.bottom
    for number, row in enumerate(rows):
        line = pygame.Rect(x, top, width, height)
        pygame.draw.rect(ui.surface, style.PARCHMENT_LIGHT if number % 2 == 0 else style.PARCHMENT, line)
        left = x
        for cell, (_, _, align), column_width in zip(row, columns, widths, strict=True):
            area = pygame.Rect(left, top, column_width, height)
            if callable(cell):
                cell(area)
            elif isinstance(cell, tuple):
                _cell(ui, area, cell[0], align, cell[1])
            else:
                _cell(ui, area, cell, align, style.INK)
            left += column_width
        if hints and number < len(hints) and hints[number]:
            ui.hint(line, *hints[number])
        top += height
    ui.rule(x, x + width, top - 1)
    return top - y


def _cell(ui: Ui, rect: pygame.Rect, text: str, align: str, color, bold: bool = False) -> None:
    pad = ui.px(7)
    font = ui.font(style.SMALL if bold else style.BODY, bold=bold)
    label = font.render(ui.fit(str(text), font, rect.width - pad * 2), True, color)
    if align == "right":
        spot = label.get_rect(midright=(rect.right - pad, rect.centery))
    elif align == "center":
        spot = label.get_rect(center=rect.center)
    else:
        spot = label.get_rect(midleft=(rect.x + pad, rect.centery))
    ui.surface.blit(label, spot)


def section(ui: Ui, title: str, x: int, y: int, width: int) -> int:
    """A section heading with a rule; returns the height it took."""
    label = ui.text(title.upper(), (x, y), style.SMALL, style.SLATE, bold=True)
    ui.rule(label.right + ui.px(8), x + width, label.centery, style.RULE)
    return label.height + ui.px(8)


def facts(ui: Ui, x: int, y: int, width: int, pairs: Sequence[tuple[str, str]], columns: int = 2) -> int:
    """Label and value pairs in columns; returns the height."""
    column_width = width // columns
    line = ui.px(40)
    for i, (label, value) in enumerate(pairs):
        left = x + (i % columns) * column_width
        top = y + (i // columns) * line
        ui.text(label.upper(), (left, top), 11, style.INK_MUTED, bold=True)
        value_text = value[0] if isinstance(value, tuple) else value
        color = value[1] if isinstance(value, tuple) else style.INK
        ui.text(value_text, (left, top + ui.px(14)), style.BODY, color, width=column_width - ui.px(10))
    rows = (len(pairs) + columns - 1) // columns
    return rows * line
