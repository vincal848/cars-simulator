"""The collapsible objectives panel under the top bar, on the right."""

from typing import TYPE_CHECKING

import pygame

from cars.sim.objectives import ACTIVE, campaign_stage, controlled_cities
from cars.ui.palette import ROUTE_GOLD, WELL

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

STATUS_TITLES = {
    "active": "Establish a lasting dominion",
    "victory": "VICTORY — Dominion secured",
    "defeat": "DEFEAT — Your realm has fallen",
}


class ObjectivesPanel:
    button = pygame.Rect(888, 52, 300, 28)
    rect = pygame.Rect(888, 84, 300, 218)

    def __init__(self, theme: "Theme") -> None:
        self.theme = theme
        self.collapsed = False

    def blocks(self, point) -> bool:
        return self.button.collidepoint(point) or (not self.collapsed and self.rect.collidepoint(point))

    def toggle(self) -> None:
        self.collapsed = not self.collapsed

    def draw(self, state: "GameState") -> None:
        goal = state.objectives
        if not goal.get("player"):
            return
        t = self.theme
        t.button(self.button, "Objectives  +" if self.collapsed else "Objectives  -")
        if self.collapsed:
            return
        x, y = self.rect.topleft
        t.panel(self.rect)
        stage = campaign_stage(state)
        t.text("The Crown’s Ambition", x + 16, y + 12, t.serif)
        cities = controlled_cities(state, goal["player"])
        rules, status = goal["rules"], goal["status"]
        heading = f"{stage.index + 1}. {stage.name}" if status == ACTIVE else STATUS_TITLES[status]
        t.text(heading, x + 16, y + 45, t.body, ROUTE_GOLD, width=268)
        t.hint((x + 16, y + 40, 268, 26), "Campaign stage", stage.goal)
        t.text(
            f"Control {rules['cities']} cities for {rules['turns']} consecutive rounds.",
            x + 16,
            y + 70,
            t.small,
            width=268,
        )
        t.text(
            f"Cities: {len(cities)} / {rules['cities']}    Rounds held: {goal['held']} / {rules['turns']}",
            x + 16,
            y + 94,
            t.body,
            width=268,
        )
        pygame.draw.rect(t.screen, WELL, (x + 16, y + 120, 268, 7))
        progress = min(1, goal["held"] / rules["turns"])
        pygame.draw.rect(t.screen, ROUTE_GOLD, (x + 16, y + 120, int(268 * progress), 7))
        for i, city in enumerate(cities[:2]):
            t.text(city.name, x + 18, y + 137 + i * 20, t.small, width=264)
        if not cities:
            t.text("Capture a city to begin your dominion.", x + 18, y + 140, t.small)
        remaining = max(0, rules["turns"] - goal["held"])
        if status == ACTIVE and len(cities) >= rules["cities"]:
            footer = f"{remaining} full rounds to secure dominion"
        else:
            footer = stage.goal
        t.text(footer, x + 16, y + 182, t.small, ROUTE_GOLD, width=268)
        t.text("Click the date for campaign stages", x + 16, y + 202, t.small, width=268)
        t.hint(
            (x + 12, y + 67, 276, 131),
            "Dominion objective",
            f"Control at least {rules['cities']} cities for {rules['turns']} consecutive full rounds. "
            "The streak updates when your next turn begins. Dropping below the city target resets it.",
        )
