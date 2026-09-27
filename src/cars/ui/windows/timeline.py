"""The campaign calendar: the season, how a turn unfolds and the path to dominion."""

import pygame

from cars.sim.calendar import date_label
from cars.sim.objectives import campaign_stage
from cars.ui.frames import Window
from cars.ui.kit import style
from cars.ui.kit.grid import section

STAGES = ("Foothold", "Expansion", "Consolidation", "Dominion")
TURN = (
    "Issue orders and develop your nation at your own pace.",
    "End Turn collects production, pays upkeep and hands play to the seven rivals.",
    "The next date refreshes movement and counts your city-holding streak.",
)


class TimelineWindow(Window):
    name = "timeline"
    title = "Campaign calendar"
    icon = "end"
    fit_content = True
    size = (660, 520)

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        state = self.state
        clock = state.clock
        x, y, width = rect.x, rect.y, rect.width
        ui.text(date_label(clock), (x, y), style.TITLE, style.SLATE, bold=True)
        ui.text(
            f"Round {clock['elapsed'] + 1}  ·  next: {date_label(clock, 1)}",
            (x, y + ui.px(34)),
            style.BODY,
            style.INK_MUTED,
        )
        y += ui.px(66)
        periods = clock["periods"]
        current = clock["elapsed"] % len(periods)
        step = width // len(periods)
        for i, period in enumerate(periods):
            cell = pygame.Rect(x + i * step, y, step - ui.px(6), ui.px(34))
            ui.button(cell, period or "Year", selected=i == current)
        y += ui.px(52)
        y += section(ui, "A turn", x, y, width)
        for i, line in enumerate(TURN):
            ui.text(f"{i + 1}.", (x, y), style.BODY, style.SLATE, bold=True)
            y += ui.paragraph(
                line, pygame.Rect(x + ui.px(24), y, width - ui.px(24), ui.px(60)), style.BODY
            ) + ui.px(4)
        y += ui.px(10)
        y += section(ui, "The path to dominion", x, y, width)
        stage = campaign_stage(state)
        step = width // len(STAGES)
        for i, name in enumerate(STAGES):
            reached = i <= stage.index
            bar = pygame.Rect(x + i * step, y, step - ui.px(8), ui.px(8))
            pygame.draw.rect(
                ui.surface, style.HIGHLIGHT if reached else style.PARCHMENT_DARK, bar, border_radius=ui.px(4)
            )
            ui.text(
                name,
                (bar.x, bar.bottom + ui.px(6)),
                style.BODY,
                style.INK if reached else style.INK_FAINT,
                bold=i == stage.index,
            )
        y += ui.px(46)
        ui.text(f"Now: {stage.name}", (x, y), style.HEADING, style.SLATE, bold=True)
        y += ui.px(26)
        y += ui.paragraph(stage.goal, pygame.Rect(x, y, width, ui.px(60)), style.BODY)
        return y - rect.y
