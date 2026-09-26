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

    def click_title(self, name: str) -> bool:
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.title.buttons[name].center)
        return self.title.event(event)

    def key_title(self, key: int) -> bool:
        return self.title.event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_new_campaign_and_display_toggle(self):
        self.click_title("display")
        self.assertTrue(self.context.display_toggle_requested)
        self.assertTrue(self.title.active)
        self.click_title("new")
        self.assertFalse(self.title.active)

    def test_help_and_quit(self):
        self.click_title("help")
        self.assertTrue(self.title.help)
        self.title.draw()
        self.key_title(pygame.K_ESCAPE)
        self.assertFalse(self.title.help)
        self.assertFalse(self.click_title("quit"))

    def test_library_needs_an_existing_save(self):
        with patch.object(self.title.library, "has_save", return_value=False):
            self.click_title("load")
            self.assertIsNone(self.game.dialogs.mode)
        with patch.object(self.title.library, "has_save", return_value=True):
            self.click_title("load")
            self.assertEqual(self.game.dialogs.mode, "load")
        self.assertTrue(self.title.active)

    def test_enter_starts_and_f1_opens_the_library(self):
        self.key_title(pygame.K_F1)
        self.assertEqual(self.game.dialogs.mode, "pedia")
        self.game.dialogs.close()
        self.key_title(pygame.K_RETURN)
        self.assertFalse(self.title.active)

    def test_tutorial_starts_a_fresh_campaign(self):
        self.click_title("tutorial")
        self.assertFalse(self.title.active)
        self.assertEqual(self.game.campaign.player, "f0")
        self.assertTrue(self.game.state.tutorial["active"])


if __name__ == "__main__":
    unittest.main()
