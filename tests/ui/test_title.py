import unittest
from unittest.mock import patch

import pygame

from cars.ui.screens.title import TitleScreen
from tests.ui.screen_case import ScreenTestCase


class TitleTests(ScreenTestCase):
    faction = None

    def setUp(self):
        super().setUp()
        self.title = TitleScreen(self.context, self.game)
        self.title.draw()

    def click_title(self, name: str) -> bool:
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.title.buttons[name].center)
        return self.title.event(event)

    def key_title(self, key: int) -> bool:
        return self.title.event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_new_campaign_then_the_nation_picker(self):
        self.click_title("new")
        self.assertFalse(self.title.active)
        self.assertEqual(self.game.window_name, "picker")

    def test_quit(self):
        self.assertFalse(self.click_title("quit"))

    def test_loading_needs_an_existing_save(self):
        with patch.object(self.title.library, "has_save", return_value=False):
            self.title.draw()
            self.assertNotIn("load", self.title.buttons)
        with patch.object(self.title.library, "has_save", return_value=True):
            self.title.draw()
            self.click_title("load")
            self.assertEqual(self.game.window_name, "load")
        self.assertTrue(self.title.active)

    def test_windows_over_the_title_take_the_input(self):
        self.key_title(pygame.K_F1)
        self.assertEqual(self.game.window_name, "pedia")
        self.title.draw()
        self.key_title(pygame.K_ESCAPE)
        self.assertEqual(self.game.window_name, "picker")  # Back to waiting for a nation.
        self.key_title(pygame.K_RETURN)
        self.assertFalse(self.title.active)

    def test_tutorial_starts_a_fresh_campaign(self):
        self.click_title("tutorial")
        self.assertFalse(self.title.active)
        self.assertEqual(self.game.campaign.player, "f0")
        self.assertTrue(self.game.state.tutorial["active"])


if __name__ == "__main__":
    unittest.main()
