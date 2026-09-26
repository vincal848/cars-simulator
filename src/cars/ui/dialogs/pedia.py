"""CARSapedia: a searchable guide to the rules, unit charters and campaign history."""

import pygame

from cars.paths import load_content
from cars.sim.entities import UNIT_STATS
from cars.sim.recruitment import RECRUITS
from cars.sim.regional import CHARTERS
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import DIM, GOLD
from cars.ui.text import wrap

SECTIONS = ("Guides", "Units", "History")
PAGE_SIZE = 8
QUERY_LIMIT = 80
SECTION_BUTTONS = {name: pygame.Rect(268 + i * 224, 181, 216, 30) for i, name in enumerate(SECTIONS)}
SEARCH_BOX = pygame.Rect(268, 221, 580, 31)
CLEAR_BUTTON = pygame.Rect(858, 221, 74, 31)
TOPIC_LIST = pygame.Rect(268, 263, 215, 304)
TOPIC_ROW = 38
PREVIOUS_BUTTON = pygame.Rect(268, 594, 94, 30)
NEXT_BUTTON = pygame.Rect(373, 594, 110, 30)
CHRONICLE_BUTTON = pygame.Rect(704, 600, 225, 30)


def _build_entries() -> list[dict]:
    entries = load_content("text", "carsapedia.json")
    notes = load_content("text", "unit_notes.json")
    for kind, spec in RECRUITS.items():
        entries.append(
            dict(
                id="unit-" + kind,
                title=spec["name"],
                category="Units",
                kind=kind,
                body=spec["role"] + ". " + notes[kind],
            )
        )
    for charter in CHARTERS.values():
        entries.append(
            dict(
                id="regional-" + charter.id,
                title=charter.name,
                category="Units",
                kind=charter.kind,
                regional=charter.id,
                body=charter.history
                + f" Recruit in a controlled city of {charter.region} using Muster / Regional. "
                "Costs two more of each resource than its base role, with "
                f"{charter.discount:.0%} lower terrain movement cost in {charter.terrain}. "
                "River and ZOC penalties still apply.",
            )
        )
    return entries


ENTRIES = _build_entries()


def search(query: str, section: str | None = None) -> list[dict]:
    """Entries in ``section`` (all sections if None) containing every word of ``query``."""
    terms = query.casefold().split()

    def in_section(entry: dict) -> bool:
        if section is None:
            return True
        if section in ("Units", "History"):
            return entry["category"] == section
        return entry["category"] not in ("Units", "History")

    def matches(entry: dict) -> bool:
        haystack = (entry["title"] + " " + entry["category"] + " " + entry["body"]).casefold()
        return all(term in haystack for term in terms)

    return [entry for entry in ENTRIES if in_section(entry) and matches(entry)]


class PediaDialog(Dialog):
    title = "CARSapedia"
    seal = "reports"
    text_input = True

    def __init__(self, game) -> None:
        super().__init__(game)
        self.query = ""
        self.index = 0
        self.scroll = 0
        self.section = "Guides"

    def results(self) -> list[dict]:
        return search(self.query, self.section)

    def _select(self, index: int) -> None:
        self.index = index
        self.scroll = 0

    def handle(self, event: pygame.event.Event) -> None:
        clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        if clicked and self.buttons["close"].collidepoint(event.pos):
            self.game.dialogs.close()
        elif clicked and self.section == "History" and CHRONICLE_BUTTON.collidepoint(event.pos):
            self.game.dialogs.open("reports")
            self.game.dialogs.active.battles_only = False
        elif event.type == pygame.TEXTINPUT:
            self.query = (self.query + event.text)[:QUERY_LIMIT]
            self._select(0)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.query = self.query[:-1]
                self._select(0)
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                step = 1 if event.key == pygame.K_DOWN else -1
                self._select(max(0, min(len(self.results()) - 1, self.index + step)))
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * 2)
        elif clicked:
            self._click(event.pos)

    def _click(self, point) -> None:
        for name, rect in SECTION_BUTTONS.items():
            if rect.collidepoint(point):
                self.section = name
                self.query = ""
                self._select(0)
                return
        page_start = (self.index // PAGE_SIZE) * PAGE_SIZE
        if CLEAR_BUTTON.collidepoint(point):
            self.query = ""
            self._select(0)
        elif TOPIC_LIST.collidepoint(point):
            self._select(min(len(self.results()) - 1, page_start + (point[1] - TOPIC_LIST.y) // TOPIC_ROW))
        elif PREVIOUS_BUTTON.collidepoint(point):
            self._select(max(0, self.index - PAGE_SIZE))
        elif NEXT_BUTTON.collidepoint(point):
            self._select(min(max(0, len(self.results()) - 1), self.index + PAGE_SIZE))

    def draw(self) -> None:
        t = self.theme
        entries = self.results()
        self.index = max(0, min(len(entries) - 1, self.index))
        for name, rect in SECTION_BUTTONS.items():
            t.button(rect, name, self.section == name)
        t.inset(SEARCH_BOX)
        t.text(self.query or "Type to search this section...", 280, 227, t.body, width=554)
        t.button(CLEAR_BUTTON, "Clear")
        page_start = (self.index // PAGE_SIZE) * PAGE_SIZE
        for row, entry in enumerate(entries[page_start : page_start + PAGE_SIZE]):
            box = pygame.Rect(268, 263 + row * TOPIC_ROW, 215, 34)
            t.button(box, "", page_start + row == self.index)
            t.text(entry["title"], box.x + 8, box.y + 9, t.small, width=199)
        t.button(PREVIOUS_BUTTON, "Previous")
        t.button(NEXT_BUTTON, "Next")
        if not entries:
            t.text("No topics found. Try a shorter search.", 500, 280, t.body, width=419)
            return
        entry = entries[self.index]
        t.text(entry["title"], 506, 272, t.heading, GOLD, width=414)
        body_top, visible_lines = 313, 12
        if "kind" in entry:
            self._draw_unit_plate(entry)
            body_top, visible_lines = 432, 7
        lines = wrap(entry["body"], t.body, 413)
        self.scroll = min(self.scroll, max(0, len(lines) - visible_lines))
        for i, line in enumerate(lines[self.scroll : self.scroll + visible_lines]):
            t.text(line, 506, body_top + i * 23, t.body)
        if self.section == "History":
            t.button(CHRONICLE_BUTTON, "Campaign Chronicle / J")
        else:
            t.text("Scroll text / Up & Down: topics / Esc: close", 506, 624, t.small, DIM, width=414)

    def _draw_unit_plate(self, entry: dict) -> None:
        """Portrait and statistics of the unit an entry describes, in the reader's colours."""
        t = self.theme
        state = self.game.state
        faction = state.factions[self.game.campaign.player or state.active]
        kind = entry["kind"]
        stats = UNIT_STATS[kind]
        charter = CHARTERS.get(entry.get("regional", ""))
        t.inset((506, 310, 92, 105))
        icon = self.game.renderer.map.sprites.sprite(
            kind, faction.color, charter.style if charter else faction.style
        )
        t.screen.blit(pygame.transform.scale(icon, (80, 88)), (512, 318))
        facts = (
            kind.title(),
            f"Movement {stats['allowance']}",
            f"Attack {stats['attack']} / Guard {stats['defense']}",
            charter.region if charter else "Standard service",
        )
        for i, line in enumerate(facts):
            t.text(line, 613, 315 + i * 23, t.body, width=310)
