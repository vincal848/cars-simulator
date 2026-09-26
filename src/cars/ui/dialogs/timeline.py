"""The campaign calendar: the current season and progress along the path to dominion."""

import pygame

from cars.sim.calendar import date_label
from cars.sim.objectives import campaign_stage
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import DIM, GOLD

STAGES = (
    ("Foothold", "province"),
    ("Expansion", "province"),
    ("Consolidation", "reports"),
    ("Dominion", "gold"),
)
UNREACHED = (83, 62, 47)


class TimelineDialog(Dialog):
    title = "The Campaign Calendar"
    seal = "end"

    def draw(self) -> None:
        t = self.theme
        clock = self.game.state.clock
        stage = campaign_stage(self.game.state)
        t.text(date_label(clock), 270, 190, t.serif, GOLD)
        t.text(f"Campaign round {clock['elapsed'] + 1} / Next: {date_label(clock, 1)}", 270, 224, t.body, DIM)
        periods = clock["periods"]
        current = clock["elapsed"] % len(periods)
        width = 640 // len(periods)
        for i, period in enumerate(periods):
            t.button(pygame.Rect(270 + i * width, 260, width - 8, 37), period or "Year", i == current)
        t.rule(270, 321, 652)
        t.text("THE PATH TO DOMINION", 270, 337, t.small, GOLD)
        for i, (label, seal) in enumerate(STAGES):
            x = 270 + i * 165
            t.seal(seal, (x + 17, 388), 30)
            t.text(label, x + 38, 380, t.small, GOLD if i == stage.index else DIM)
            pygame.draw.line(t.screen, GOLD if i <= stage.index else UNREACHED, (x, 414), (x + 146, 414), 3)
        t.text("Current stage: " + stage.name, 270, 439, t.heading, GOLD)
        t.text(stage.goal, 270, 471, t.body, width=650)
        t.text("1. Issue orders and develop your realm at your own pace.", 270, 522, t.body)
        t.text("2. End Turn collects production and hands play to seven rivals.", 270, 549, t.body)
        t.text("3. The next date refreshes orders and checks your city-holding streak.", 270, 576, t.body)
        t.text(
            "Stages follow your position, not fixed dates; losses can set progress back.",
            270,
            624,
            t.small,
            DIM,
        )
