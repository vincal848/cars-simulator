"""A campaign screen on a hidden display, for UI tests."""

import unittest

import pygame

from cars.sim.scenario import COMPACT_SCENARIO, load_scenario
from cars.ui.context import UiContext
from cars.ui.screens.game import GameScreen
from tests.support import SCREEN_SIZE


class ScreenTestCase(unittest.TestCase):
    """A campaign screen on a hidden display, with the player's faction already chosen."""

    scenario = COMPACT_SCENARIO
    faction: str | None = "f0"

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.state, self.shapes, self.seas = load_scenario(self.scenario)
        self.context = UiContext(self.screen)
        self.game = GameScreen(self.context, self.state, self.shapes, self.seas)
        if self.faction:
            self.game.choose_faction(self.faction)

    def tearDown(self) -> None:
        pygame.quit()

    @property
    def renderer(self):
        return self.game.renderer

    @property
    def map(self):
        return self.game.renderer.map

    def send(self, kind: int, **data) -> bool:
        return self.game.event(pygame.event.Event(kind, data))

    def press(self, point, button: int = 1) -> None:
        self.send(pygame.MOUSEBUTTONDOWN, button=button, pos=tuple(point))

    def click(self, point, button: int = 1) -> None:
        """A full click; map clicks only act on release."""
        self.press(point, button)
        self.send(pygame.MOUSEBUTTONUP, button=button, pos=tuple(point))

    def key(self, key: int) -> None:
        self.send(pygame.KEYDOWN, key=key)

    def draw(self, hover=None) -> None:
        self.game.draw(hover)

    def finish_rival_turns(self, dt: float = 1.0, limit: int = 400) -> None:
        for _ in range(limit):
            self.game.update(dt)
            if self.game.campaign.human_turn:
                return
        self.fail("Rival turns did not finish")
