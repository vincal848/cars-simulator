"""The CARSapedia window: search, a list grouped by category, and articles with links.

Links in the text jump to other articles; Back and Forward walk the reading
history. Any part of the interface can open an article directly with
``GameScreen.open_pedia``.
"""

import re

import pygame

from cars.sim.regional import CHARTERS
from cars.ui.art.paintings import LEADERS, frame, painting
from cars.ui.frames import Window
from cars.ui.kit import style
from cars.ui.kit.grid import draw_grid, facts, section
from cars.ui.pedia.library import CATEGORIES, LINK, Article, build, search

LIST_WIDTH = 290
QUERY_LIMIT = 60
HOME = "welcome"
INDEXES = ("nations", "units", "buildings")
INDEXED = ("Nations", "Units", "Regional charters", "Buildings", "Terrain", "Events")


class PediaWindow(Window):
    name = "pedia"
    title = "CARSapedia"
    icon = "pedia"
    size = (1180, 760)
    text_input = True

    def __init__(self, game) -> None:
        super().__init__(game)
        self.library: dict[str, Article] = build({f.id: f.name for f in game.state.factions.values()})
        self.query = ""
        self.history = [HOME]
        self.position = 0
        self.open_categories = {"Getting started"}
        self.list_scroll = 0
        self.article_scroll = 0
        self._list_rect = pygame.Rect(0, 0, 0, 0)

    @property
    def current(self) -> Article:
        return self.library.get(self.history[self.position], self.library[HOME])

    def go(self, article_id: str) -> None:
        """Open an article, dropping any forward history."""
        if article_id not in self.library or article_id == self.history[self.position]:
            return
        self.history = [*self.history[: self.position + 1], article_id]
        self.position = len(self.history) - 1
        self.article_scroll = 0
        self.open_categories.add(self.library[article_id].category)

    # Drawing ----------------------------------------------------------------------------

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        listing = pygame.Rect(rect.x, rect.y, ui.px(LIST_WIDTH), rect.height)
        article = pygame.Rect(
            listing.right + ui.px(20), rect.y, rect.right - listing.right - ui.px(20), rect.height
        )
        self._draw_list(ui, listing)
        pygame.draw.line(
            ui.surface,
            style.RULE,
            (listing.right + ui.px(10), rect.y),
            (listing.right + ui.px(10), rect.bottom),
        )
        self._draw_article(ui, article)
        return rect.height  # Each pane scrolls on its own.

    def _draw_list(self, ui, rect: pygame.Rect) -> None:
        box = pygame.Rect(rect.x, rect.y, rect.width, ui.px(34))
        ui.inset(box)
        ui.icon("pedia", (box.x + ui.px(16), box.centery), 16, style.INK_MUTED)
        text = self.query + "|" if self.query else "Search the library…"
        ui.text(
            text,
            (box.x + ui.px(32), box.centery - ui.px(10)),
            style.BODY,
            style.INK if self.query else style.INK_FAINT,
            width=box.width - ui.px(60),
        )
        if self.query:
            clear = pygame.Rect(box.right - ui.px(28), box.y + ui.px(5), ui.px(24), ui.px(24))
            ui.text("×", (clear.centerx, clear.y), style.HEADING, style.INK_MUTED, align="center")
            self.clickable(clear, "clear")
        area = pygame.Rect(rect.x, box.bottom + ui.px(10), rect.width, rect.bottom - box.bottom - ui.px(10))
        self._list_rect = area
        rows = self._list_rows()
        row_height = ui.px(28)
        self.list_scroll = max(0, min(self.list_scroll, len(rows) * row_height - area.height))
        with ui.clip(area):
            y = area.y - self.list_scroll
            for kind, value, label in rows:
                line = pygame.Rect(area.x, y, area.width, row_height)
                if line.bottom >= area.top and line.top <= area.bottom:
                    self._list_row(ui, line, kind, value, label)
                y += row_height

    def _list_rows(self) -> list[tuple[str, str, str]]:
        if self.query:
            results = search(self.library, self.query)
            return [("article", a.id, a.title) for a in results] or [("empty", "", "Nothing matches.")]
        rows = []
        for category in CATEGORIES:
            articles = _ordered(self.library, category)
            if not articles:
                continue
            rows.append(("category", category, f"{category}  ({len(articles)})"))
            if category in self.open_categories:
                rows += [("article", a.id, a.title) for a in articles]
        return rows

    def _list_row(self, ui, line: pygame.Rect, kind: str, value: str, label: str) -> None:
        pad = ui.px(8)
        if kind == "category":
            pygame.draw.rect(ui.surface, style.PANEL_DARK, line.inflate(0, -ui.px(2)), border_radius=ui.px(3))
            ui.disclosure((line.x + pad + ui.px(4), line.centery), value in self.open_categories, style.SLATE)
            ui.text(
                label,
                (line.x + pad * 2 + ui.px(8), line.centery - ui.px(9)),
                style.BODY,
                style.SLATE,
                bold=True,
                width=line.width - pad * 3,
            )
            self._list_click(line, "category:" + value)
        elif kind == "article":
            current = value == self.current.id
            if current:
                pygame.draw.rect(ui.surface, style.SELECTED_ROW, line, border_radius=ui.px(3))
            elif ui.hovered(line) and self._list_rect.collidepoint(ui.mouse()):
                pygame.draw.rect(ui.surface, style.HOVER_ROW, line, border_radius=ui.px(3))
            indent = 0 if self.query else pad * 2
            ui.text(
                label,
                (line.x + pad + indent, line.centery - ui.px(9)),
                style.BODY,
                style.INK,
                bold=current,
                width=line.width - pad * 2 - indent,
            )
            self._list_click(line, "goto:" + value)
        else:
            ui.text(label, (line.x + pad, line.centery - ui.px(9)), style.BODY, style.INK_FAINT)

    def _list_click(self, line: pygame.Rect, action: str) -> None:
        visible = line.clip(self._list_rect)
        if visible.height:
            self.areas.append((visible, action))

    def _draw_article(self, ui, rect: pygame.Rect) -> None:
        article = self.current
        toolbar = pygame.Rect(rect.x, rect.y, rect.width, ui.px(30))
        back = pygame.Rect(toolbar.x, toolbar.y, ui.px(80), toolbar.height)
        forward = pygame.Rect(back.right + ui.px(6), toolbar.y, ui.px(92), toolbar.height)
        self.button(back, "‹ Back", "back", enabled=self.position > 0)
        self.button(forward, "Forward ›", "forward", enabled=self.position < len(self.history) - 1)
        ui.text(
            f"{article.category}  ›  {article.title}",
            (forward.right + ui.px(14), toolbar.centery - ui.px(9)),
            style.BODY,
            style.INK_MUTED,
            width=rect.right - forward.right - ui.px(14),
        )
        page = pygame.Rect(
            rect.x, toolbar.bottom + ui.px(12), rect.width, rect.bottom - toolbar.bottom - ui.px(12)
        )
        self._page = page
        with ui.clip(page):
            height = self._draw_page(ui, article, page.move(0, -self.article_scroll))
        self.article_scroll = max(0, min(self.article_scroll, height - page.height))
        if height > page.height:
            track = pygame.Rect(page.right - ui.px(4), page.y, ui.px(4), page.height)
            thumb = track.copy()
            thumb.height = max(ui.px(24), page.height * page.height // height)
            thumb.y = page.y + (page.height - thumb.height) * self.article_scroll // max(
                1, height - page.height
            )
            pygame.draw.rect(ui.surface, style.PANEL_DARK, track, border_radius=track.width // 2)
            pygame.draw.rect(ui.surface, style.ACCENT, thumb, border_radius=track.width // 2)

    def _draw_page(self, ui, article: Article, rect: pygame.Rect) -> int:
        x, y = rect.x, rect.y
        width = rect.width - ui.px(14)
        plate_width = 0
        if article.plate:
            plate_width = self._plate(
                ui, article.plate, pygame.Rect(x + width - ui.px(150), y, ui.px(150), ui.px(170))
            )
        text_width = width - (plate_width + ui.px(16) if plate_width else 0)
        ui.text(article.title, (x, y), style.TITLE + 4, style.SLATE, bold=True, width=text_width)
        y += ui.px(42)
        if article.summary:
            y += ui.paragraph(
                article.summary, pygame.Rect(x, y, text_width, ui.px(80)), style.BODY, style.INK_MUTED
            ) + ui.px(8)
        if article.facts:
            y += facts(ui, x, y, text_width, [(label, self._plain(value)) for label, value in article.facts])
            y += ui.px(6)
        if plate_width:
            y = max(y, rect.y + ui.px(180))
        for paragraph in article.body:
            y += self._rich(ui, paragraph, x, y, width) + ui.px(10)
        for title, columns, rows in article.tables:
            y += ui.px(6)
            y += section(ui, title, x, y, width)
            specs = [
                (column, 160 if i == 0 and len(columns) > 1 else None, "left")
                for i, column in enumerate(columns)
            ]
            y += draw_grid(
                ui, x, y, width, specs, [[self._cell(ui, cell) for cell in row] for row in rows]
            ) + ui.px(10)
        if article.see_also:
            y += ui.px(6)
            y += section(ui, "See also", x, y, width)
            chip_x = x
            for target in article.see_also:
                label = self.library[target].title
                font = ui.font(style.BODY)
                chip = pygame.Rect(chip_x, y, font.size(label)[0] + ui.px(20), ui.px(28))
                if chip.right > x + width:
                    chip_x, y = x, y + ui.px(34)
                    chip.topleft = (chip_x, y)
                self.button(chip, label, "goto:" + target)
                chip_x = chip.right + ui.px(8)
            y += ui.px(40)
        return y - rect.y

    def _plate(self, ui, plate: tuple, rect: pygame.Rect) -> int:
        state = self.state
        ui.inset(rect)
        if plate[0] == "unit":
            faction = state.factions[self.game.campaign.player or state.active]
            uniform = CHARTERS[plate[2]].style if plate[2] else faction.style
            sprite = self.game.renderer.map.sprites.sprite(plate[1], faction.color, uniform)
            size = min(rect.width, rect.height) - ui.px(20)
            ui.surface.blit(
                pygame.transform.smoothscale(sprite, (size, size)),
                (rect.centerx - size // 2, rect.centery - size // 2),
            )
        else:
            faction = state.factions[plate[1]]
            portrait = painting(LEADERS, plate[1], (rect.width - ui.px(16), rect.height - ui.px(16)))
            if portrait:
                frame(ui.surface, portrait, rect.inflate(-ui.px(16), -ui.px(16)))
            else:
                ui.swatch(rect.center, faction.color, 48)
                ui.icon("nation", rect.center, 50, style.ON_SLATE)
        return rect.width

    # Rich text --------------------------------------------------------------------------

    @staticmethod
    def _plain(text: str) -> str:
        return LINK.sub(lambda m: m.group(2) or m.group(1), text)

    def _cell(self, ui, text: str):
        match = LINK.fullmatch(text)
        if not match:
            return self._plain(text)
        target, label = match.group(1), match.group(2) or self.library[match.group(1)].title

        def draw(area: pygame.Rect) -> None:
            pad = ui.px(7)
            rendered = ui.text(
                label,
                (area.x + pad, area.centery - ui.px(9)),
                style.BODY,
                style.SLATE,
                bold=True,
                width=area.width - pad * 2,
            )
            pygame.draw.line(
                ui.surface, style.SLATE, rendered.bottomleft, rendered.bottomright, max(1, ui.px(1))
            )
            self._link_area(rendered, target)

        return draw

    def _link_area(self, rect: pygame.Rect, target: str) -> None:
        visible = rect.clip(self._page)
        if visible.height:
            self.areas.append((visible, "goto:" + target))

    def _rich(self, ui, text: str, x: int, y: int, width: int) -> int:
        """A paragraph whose ``[[links]]`` are drawn as clickable words; returns its height."""
        tokens: list[tuple[str, str | None, bool]] = []  # (word, link target, space before)
        position = 0
        for match in LINK.finditer(text):
            tokens += _words(text[position : match.start()], None)
            label = match.group(2) or self.library[match.group(1)].title
            tokens += _words(
                (" " if match.start() and text[match.start() - 1] == " " else "") + label, match.group(1)
            )
            position = match.end()
        tokens += _words(text[position:], None)
        plain, linked = ui.font(style.BODY), ui.font(style.BODY, bold=True)
        space = plain.size(" ")[0]
        line_height = round(plain.get_height() * 1.4)
        cursor_x, cursor_y = x, y
        for index, (word, target, spaced) in enumerate(tokens):
            font = linked if target else plain
            word_width = font.size(word)[0]
            if index and spaced:
                cursor_x += space
            if cursor_x > x and cursor_x + word_width > x + width:
                cursor_x, cursor_y = x, cursor_y + line_height
            color = style.SLATE if target else style.INK
            rendered = ui.surface.blit(font.render(word, True, color), (cursor_x, cursor_y))
            if target:
                bottom = rendered.bottom - 1
                pygame.draw.line(
                    ui.surface, style.SLATE, (rendered.x, bottom), (rendered.right, bottom), max(1, ui.px(1))
                )
                self._link_area(rendered.inflate(space, 0), target)
            cursor_x += word_width
        return cursor_y + line_height - y

    # Input ------------------------------------------------------------------------------

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEWHEEL:
            step = self.ui.px(48) * event.y
            if self._list_rect.collidepoint(self.ui.mouse()):
                self.list_scroll = max(0, self.list_scroll - step)
            else:
                self.article_scroll = max(0, self.article_scroll - step)
            return True
        return super().handle(event)

    def handle_other(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.TEXTINPUT:
            self.query = (self.query + event.text)[:QUERY_LIMIT]
            self.list_scroll = 0
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.query = self.query[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.query:
                results = search(self.library, self.query)
                if results:
                    self.go(results[0].id)
            elif event.key == pygame.K_LEFT and event.mod & pygame.KMOD_ALT:
                self.act("back")
            elif event.key == pygame.K_RIGHT and event.mod & pygame.KMOD_ALT:
                self.act("forward")
            return True
        return False

    def act(self, action: str) -> None:
        verb, _, value = action.partition(":")
        if verb == "goto":
            self.go(value)
        elif verb == "category":
            self.open_categories ^= {value}
        elif verb == "clear":
            self.query = ""
        elif verb == "back" and self.position > 0:
            self.position -= 1
            self.article_scroll = 0
        elif verb == "forward" and self.position < len(self.history) - 1:
            self.position += 1
            self.article_scroll = 0


def _words(text: str, target: str | None) -> list[tuple[str, str | None, bool]]:
    """``text`` split into words, each noting whether a space came before it."""
    return [(m.group(2), target, bool(m.group(1))) for m in re.finditer(r"(\s*)(\S+)", text)]


def _ordered(library: dict[str, Article], category: str) -> list[Article]:
    """A category's articles: authored ones in the order they were written, generated ones
    alphabetically after their index page."""
    articles = [a for a in library.values() if a.category == category]
    if category in INDEXED:
        return sorted(articles, key=lambda a: (a.id not in INDEXES, a.title))
    return articles
