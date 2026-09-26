import json
import tempfile
import unittest
from pathlib import Path

import pygame

from cars.persist.replay import Playback, digest
from cars.persist.savegame import load_game, save_game
from cars.sim.movement import reachable
from cars.sim.scenario import DETAILED_SCENARIO
from cars.ui.text import wrap
from cars.ui.tutorial import LESSONS
from tests.ui.screen_case import ScreenTestCase


class TutorialTests(ScreenTestCase):
    scenario = DETAILED_SCENARIO
    faction = None

    def setUp(self):
        super().setUp()
        self.game.start_tutorial()
        self.tutorial = self.game.tutorial

    def click_card(self, name: str) -> None:
        self.tutorial.event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.tutorial.buttons[name].center)
        )

    def complete(self, goal: str) -> None:
        self.tutorial.observe()
        self.assertIn(goal, self.game.state.tutorial["seen"])
        self.game.renderer.province_window.close()
        self.game.dialogs.close()
        self.click_card("next")

    def test_progress_is_saved_and_skipping_never_traps_the_player(self):
        progress = self.game.state.tutorial
        self.assertTrue(progress["active"])
        self.assertEqual(progress["step"], 0)
        self.game.next_ready()
        self.tutorial.observe()
        self.assertIn("select", progress["seen"])
        self.click_card("next")
        self.assertEqual(progress["step"], 1)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tutorial.json"
            save_game(self.game.state, self.renderer.shapes, self.renderer.seas, "f0", path)
            restored, *_ = load_game(path)
            self.assertEqual(restored.tutorial, progress)
        for _ in range(9):
            self.click_card("skip")
        self.assertFalse(progress["active"])

    def test_every_lesson_completes_through_real_actions(self):
        game = self.game
        game.next_ready()
        self.complete("select")
        unit = game.state.units[game.view.selected]
        destination = next(p for p in reachable(game.state, unit).costs if p != unit.location)
        game.campaign.move(unit.id, destination)
        self.complete("move")
        game.inspect(destination, (400, 300))
        self.complete("inspect")
        self.assertTrue(game.campaign.construct(destination, "farm")[0])
        self.complete("build")
        game.switch_layer("supply")
        self.complete("supply")
        city = next(
            c.province
            for c in game.state.cities.values()
            if game.state.provinces[c.province].controller == "f0"
        )
        self.assertTrue(game.campaign.recruit(city, "infantry")[0])
        self.complete("recruit")
        game.advance()
        self.finish_rival_turns()
        self.complete("turn")
        for mode in ("pedia", "strategy", "replay"):
            game.dialogs.open(mode)
            self.complete(mode)
        self.assertFalse(game.state.tutorial["active"])
        playback = Playback(game.campaign.recorder.data())
        while playback.step():
            pass
        self.assertEqual(digest(playback.state), digest(game.state))

    def test_lesson_text_fits_the_card_in_every_font(self):
        theme = self.context.theme
        for font in range(3):
            theme.set_font(font)
            for lesson in LESSONS:
                self.assertLessEqual(len(wrap(lesson.body, theme.small, 294)), 4)

    def test_malformed_progress_is_rejected_on_load(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tutorial.json"
            save_game(self.game.state, self.renderer.shapes, self.renderer.seas, "f0", path)
            data = json.loads(path.read_text())
            data["tutorial"]["seen"] = [{}]
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_game(path)


if __name__ == "__main__":
    unittest.main()
