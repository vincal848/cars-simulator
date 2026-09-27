"""The guided tutorial: ten lessons that complete when the player actually does each thing.

Progress is stored in the game state, so it survives saving; skipping never blocks play.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from cars.paths import load_content
from cars.ui.kit import style
from cars.ui.map.map_view import SUPPLY

if TYPE_CHECKING:
    from cars.ui.screens.game import GameScreen

# Journal entries that satisfy a lesson.
REPORT_GOALS = {"movement": "move", "construction": "build", "recruitment": "recruit"}
STUDY_GOALS = ("pedia", "strategy", "replay")
SIZE = (330, 206)
BUTTONS = ("next", "skip", "hide")


@dataclass(frozen=True)
class Lesson:
    title: str
    body: str
    goal: str


LESSONS = [Lesson(**lesson) for lesson in load_content("text", "tutorial.json")]


class Tutorial:
    def __init__(self, game: "GameScreen") -> None:
        self.game = game
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.buttons: dict[str, pygame.Rect] = {}

    @property
    def progress(self) -> dict:
        return self.game.state.tutorial

    def observe(self) -> None:
        """Mark lesson goals the player has achieved since the last frame."""
        progress = self.progress
        if not progress.get("active"):
            return
        game = self.game
        state, player = game.state, game.campaign.player
        seen = set(progress.get("seen", []))
        selected = state.units.get(game.view.selected)
        if selected and selected.owner == player:
            seen.add("select")
        if getattr(game.panel, "name", None) == "province":
            seen.add("inspect")
        if game.view.mode == SUPPLY and selected:
            seen.add("supply")
        if state.clock["elapsed"] > 0:
            seen.add("turn")
        if game.window_name in STUDY_GOALS:
            seen.add(game.window_name)
        for report in state.reports:
            if report["owner"] == player and report["kind"] in REPORT_GOALS:
                seen.add(REPORT_GOALS[report["kind"]])
        progress["seen"] = sorted(seen)

    def visible(self) -> bool:
        return bool(
            self.progress.get("active") and not self.progress.get("hidden") and self.game.window is None
        )

    def blocks(self, point) -> bool:
        return self.visible() and self.rect.collidepoint(point)

    def layout(self) -> None:
        ui = self.game.context.ui
        renderer = self.game.renderer
        lesson = LESSONS[min(self.progress.get("step", 0), len(LESSONS) - 1)]
        width = ui.px(SIZE[0])
        text = ui.paragraph_height(lesson.body, width - ui.px(style.PAD) * 2)
        height = ui.px(40 + 12 + 26) + text + ui.px(26 + 44)
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.bottomright = (ui.screen.right - ui.px(14), renderer.controls.rect.top - ui.px(12))
        button_width = (width - ui.px(24) - ui.px(12)) // len(BUTTONS)
        self.buttons = {
            name: pygame.Rect(
                self.rect.x + ui.px(12) + i * (button_width + ui.px(6)),
                self.rect.bottom - ui.px(40),
                button_width,
                ui.px(28),
            )
            for i, name in enumerate(BUTTONS)
        }

    def event(self, event: pygame.event.Event) -> bool:
        progress = self.progress
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            if progress.get("active"):
                progress["hidden"] = not progress.get("hidden", False)
            else:
                self.game.view.message = "Start the Guided Tutorial from the title screen."
            return True
        if (
            not self.visible()
            or event.type != pygame.MOUSEBUTTONDOWN
            or not self.rect.collidepoint(event.pos)
        ):
            return False
        if event.button == 1:
            action = next((name for name, rect in self.buttons.items() if rect.collidepoint(event.pos)), None)
            step = progress.get("step", 0)
            if action == "hide":
                progress["hidden"] = True
            elif action == "skip" or (action == "next" and LESSONS[step].goal in progress.get("seen", [])):
                progress["step"] = step + 1
                if progress["step"] >= len(LESSONS):
                    progress["active"] = False
                    self.game.view.message = "Tutorial complete. The CARSapedia (F1) explains every rule."
        return True

    def draw(self) -> None:
        if not self.visible():
            return
        self.layout()
        ui = self.game.context.ui
        step = self.progress.get("step", 0)
        lesson = LESSONS[step]
        complete = lesson.goal in self.progress.get("seen", [])
        inner = ui.panel(self.rect, f"Lesson {step + 1} of {len(LESSONS)}", "chronicle")
        ui.text(lesson.title, (inner.x, inner.y), style.HEADING, style.SLATE, bold=True, width=inner.width)
        body = pygame.Rect(inner.x, inner.y + ui.px(26), inner.width, ui.screen.height)
        ui.paragraph(lesson.body, body, style.BODY)
        status = "Done: continue when ready." if complete else "Try it on the map. H hides this card."
        ui.text(
            status,
            (inner.x, self.rect.bottom - ui.px(62)),
            style.SMALL,
            style.GOOD if complete else style.INK_MUTED,
            width=inner.width,
        )
        for name, rect in self.buttons.items():
            ui.button(
                rect,
                name.title(),
                kind="primary" if name == "next" else "secondary",
                enabled=name != "next" or complete,
            )
