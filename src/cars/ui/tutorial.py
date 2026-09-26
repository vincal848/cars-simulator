"""The guided tutorial: ten lessons that complete when the player actually does each thing.

Progress is stored in the game state, so it survives saving; skipping never blocks play.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import pygame

from cars.paths import load_content
from cars.ui.palette import DIM, GOLD
from cars.ui.text import wrap

if TYPE_CHECKING:
    from cars.ui.screens.game import GameScreen

# Journal entries that satisfy a lesson.
REPORT_GOALS = {"movement": "move", "construction": "build", "recruitment": "recruit"}
STUDY_GOALS = ("pedia", "strategy", "replay")


@dataclass(frozen=True)
class Lesson:
    title: str
    body: str
    goal: str


LESSONS = [Lesson(**lesson) for lesson in load_content("text", "tutorial.json")]


class Tutorial:
    rect = pygame.Rect(16, 443, 322, 192)
    buttons: ClassVar[dict] = {
        name: pygame.Rect(28 + i * 101, 599, 94, 27) for i, name in enumerate(("next", "skip", "hide"))
    }

    def __init__(self, game: "GameScreen") -> None:
        self.game = game

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
        if game.renderer.province_window.is_open:
            seen.add("inspect")
        if game.view.layer == "supply" and game.view.selected:
            seen.add("supply")
        if state.clock["elapsed"] > 0:
            seen.add("turn")
        if game.dialogs.mode in STUDY_GOALS:
            seen.add(game.dialogs.mode)
        for report in state.reports:
            if report["owner"] == player and report["kind"] in REPORT_GOALS:
                seen.add(REPORT_GOALS[report["kind"]])
        progress["seen"] = sorted(seen)

    def visible(self) -> bool:
        renderer = self.game.renderer
        return bool(
            self.progress.get("active")
            and not self.progress.get("hidden")
            and not self.game.dialogs.mode
            and not renderer.province_window.is_open
            and not renderer.market.open
            and not renderer.menu.open
        )

    def blocks(self, point) -> bool:
        return self.visible() and self.rect.collidepoint(point)

    def event(self, event: pygame.event.Event) -> bool:
        progress = self.progress
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            if progress.get("active"):
                progress["hidden"] = not progress.get("hidden", False)
            else:
                self.game.view.message = (
                    "Start Guided Tutorial from the title screen for the complete lesson campaign."
                )
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
                    self.game.view.message = (
                        "Tutorial complete. Continue your campaign, or explore the CARSapedia."
                    )
        return True

    def draw(self) -> None:
        if not self.visible():
            return
        t = self.game.context.theme
        step = self.progress.get("step", 0)
        lesson = LESSONS[step]
        complete = lesson.goal in self.progress.get("seen", [])
        t.panel(self.rect, True)
        t.seal("reports", (38, 464), 24)
        t.text(f"LESSON {step + 1} / {len(LESSONS)}", 58, 456, t.small, GOLD)
        t.text(lesson.title, 28, 484, t.heading, GOLD, width=296)
        for i, line in enumerate(wrap(lesson.body, t.small, 294)):
            t.text(line, 28, 512 + i * 18, t.small)
        status = "Completed - continue when ready" if complete else "Try it on the map / H hides this guide"
        t.text(status, 28, 579, t.small, DIM, width=295)
        for name, rect in self.buttons.items():
            t.button(rect, name.title(), enabled=name != "next" or complete)
