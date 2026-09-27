import os
import shutil
import unittest
from pathlib import Path

import pygame

from cars.ui.art import paintings
from cars.ui.audio import Audio
from cars.ui.windows import WINDOWS
from tests.ui.screen_case import ScreenTestCase


class WindowTests(ScreenTestCase):
    def test_every_window_draws_and_is_modal(self):
        self.context.audio = Audio()
        for name in WINDOWS:
            if name in ("event", "picker"):
                continue
            with self.subTest(window=name):
                self.game.open_window(name)
                self.draw()
                self.assertIsNone(self.game.hit((600, 400)))
                self.key(pygame.K_SPACE)
                self.assertEqual(self.state.active, "f0")  # Keys go to the window, not the campaign.
                self.key(pygame.K_ESCAPE)
                self.assertIsNone(self.game.window)

    def test_the_menu_opens_other_windows(self):
        self.game.open_window("menu")
        self.click_area(self.game.window, "settings")
        self.assertEqual(self.game.window_name, "settings")

    def test_settings_change_the_interface_size_and_remember_it(self):
        self.context.audio = Audio()
        self.game.open_window("settings")
        self.click_area(self.game.window, "scale:1.5")
        self.assertEqual(self.ui.scale, 1.5)
        self.assertEqual(self.context.audio.settings["ui_scale"], 1.5)
        self.click_area(self.game.window, "font:0")
        self.assertEqual(self.ui.font_index, 0)
        self.click_area(self.game.window, "scale:0")
        self.assertEqual(self.ui.scale, 1.0)  # Automatic at 1200 x 780.

    def test_saving_and_loading_a_slot(self):
        self.game.open_window("save")
        self.click_area(self.game.window, "slot1")
        self.assertIn("saved", self.game.window.notice)
        self.state.round = 99
        self.game.open_window("load")
        self.click_area(self.game.window, "slot1")
        self.click_area(self.game.window, "slot1")
        self.assertIsNone(self.game.window)
        self.assertEqual(self.game.state.round, 1)
        self.assertEqual(self.game.campaign.player, "f0")

    def test_the_strategic_atlas_picks_nodes(self):
        self.game.open_window("strategy")
        window = self.game.window
        self.click_area(window, "layer:supply")
        self.assertEqual(window.layer, "supply")
        self.draw()
        node, point = sorted(window.points.items())[0]
        self.context.pointer = point
        self.click(point)
        self.assertEqual(window.selected, node)


class EventWindowTests(ScreenTestCase):
    def test_a_pending_event_demands_a_decision(self):
        self.state.events["fired"].append("bountiful_harvest")
        self.state.events["pending"].append("bountiful_harvest")
        self.game.update(0.1)
        self.assertEqual(self.game.window_name, "event")
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.window_name, "event")
        gold = self.state.factions["f0"].gold
        self.click_area(self.game.window, "option:1")
        self.assertIsNone(self.game.window)
        self.assertEqual(self.state.factions["f0"].gold, gold + 35)

    def test_a_painting_illustrates_the_event_when_a_mod_supplies_one(self):
        mods = Path(os.environ["CARS_SAVE_DIR"]).parent / "mods" / "art" / "gfx" / "paintings" / "events"
        mods.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, mods.parents[2])
        image = pygame.Surface((400, 200))
        image.fill((180, 120, 60))
        pygame.image.save(image, str(mods / "lean_winter.png"))
        paintings._cache.clear()
        self.addCleanup(paintings._cache.clear)
        self.state.events["pending"].append("lean_winter")
        self.game.update(0.1)
        window = self.game.window
        self.assertIsNotNone(window.illustration())
        self.draw()
        self.assertIn(
            (180, 120, 60),
            {
                tuple(self.screen.get_at(window.rect.center)[:3]),
                tuple(self.screen.get_at((window.rect.centerx, window.body.y + 40))[:3]),
            },
        )


class RegistryTests(unittest.TestCase):
    def test_every_window_has_a_name_matching_its_key(self):
        for name, cls in WINDOWS.items():
            self.assertEqual(cls.name, name)


if __name__ == "__main__":
    unittest.main()
