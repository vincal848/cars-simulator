import tempfile
import unittest
from pathlib import Path

import pygame

from cars.persist.replay import digest
from cars.persist.savegame import SaveLibrary, load_game, save_game
from cars.sim.scenario import DETAILED_SCENARIO
from cars.ui.audio import Audio
from cars.ui.screens.replay import ReplayScreen
from tests.ui.screen_case import ScreenTestCase


class DialogTestCase(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.folder = tempfile.TemporaryDirectory()
        self.library = SaveLibrary(Path(self.folder.name))
        self.game.library = self.library
        for dialog in (self.game.dialogs.dialogs["save"], self.game.dialogs.dialogs["load"]):
            dialog.library = self.library
        self.context.audio = Audio(Path(self.folder.name) / "settings.json")

    def tearDown(self):
        super().tearDown()
        self.folder.cleanup()

    def click_button(self, name: str) -> None:
        self.click(self.game.dialogs.active.buttons[name].center)


class LibraryDialogTests(DialogTestCase):
    def test_save_asks_before_replacing_and_load_restores(self):
        dialogs = self.game.dialogs
        path = self.library.path(1)
        dialogs.open("save")
        self.click_button("slot1")
        self.assertTrue(path.exists())
        self.state.round = 4
        self.click_button("slot1")
        self.assertEqual(load_game(path)[0].round, 1)
        self.click_button("slot1")
        self.assertEqual(load_game(path)[0].round, 4)

        self.state.round = 5
        dialogs.open("load")
        self.click_button("slot1")
        self.assertEqual(self.game.state.round, 5)
        self.click_button("slot1")
        self.assertEqual(self.game.state.round, 4)
        self.assertIsNone(self.game.dialogs.mode)
        self.assertIs(self.game.renderer.state, self.game.state)
        self.assertEqual(self.game.campaign.player, "f0")

    def test_load_rebinds_the_whole_screen(self):
        path = self.library.path(0)
        save_game(self.state, self.shapes, self.seas, "f0", path)
        self.state.units["infantry0"].hp = 1
        self.key(pygame.K_F9)
        self.click_button("slot0")
        self.assertEqual(self.game.state.units["infantry0"].hp, 1)
        self.click_button("slot0")
        self.assertEqual(self.game.state.units["infantry0"].hp, 10)
        self.assertIs(self.game.renderer.campaign, self.game.campaign)
        self.game.switch_layer("supply")
        self.assertEqual(self.game.view.selected, "infantry0")
        self.draw()

    def test_autosave_after_rival_turns_unless_disabled(self):
        path = self.library.path(SaveLibrary.AUTOSAVE)
        self.game.advance()
        self.finish_rival_turns(dt=0.5)
        self.assertTrue(path.exists())
        self.assertEqual(load_game(path)[0].active, "f0")
        before = path.read_bytes()
        self.game.state.round += 1
        self.context.audio.settings["autosave"] = False
        self.game.autosave()
        self.assertEqual(path.read_bytes(), before)

    def test_modal_dialogs_capture_the_map_and_keys(self):
        for mode in ("save", "load", "settings", "reports", "roster", "timeline", "music", "replay"):
            self.game.dialogs.open(mode)
            self.assertIsNone(self.game.hit((400, 400)))
            self.draw()
            self.key(pygame.K_SPACE)
            self.assertEqual(self.state.active, "f0")
            self.key(pygame.K_ESCAPE)
            self.assertIsNone(self.game.dialogs.mode)


class SettingsTests(DialogTestCase):
    def test_volume_persists_and_mutes(self):
        audio = self.context.audio
        self.assertTrue(audio.available)
        audio.change("master", -1)
        audio.play("battle")
        self.assertEqual(audio.settings["master"], 0)
        self.assertEqual(audio.music_channel.get_volume(), 0)
        self.assertEqual(Audio(audio.path).settings["master"], 0)

    def test_collection_controls_from_settings(self):
        audio = self.context.audio
        self.game.dialogs.open("settings")
        self.click_button("collection")
        self.assertEqual(self.game.dialogs.mode, "music")
        self.click_button("track1")
        self.assertEqual(audio.index, 1)
        self.click_button("pause")
        self.assertTrue(audio.settings["paused"])
        self.click_button("next")
        self.assertEqual(audio.index, 2)
        self.draw()
        self.click_button("close")
        self.assertIsNone(self.game.dialogs.mode)


class RosterTests(ScreenTestCase):
    def test_filters_and_click_to_focus(self):
        dialogs = self.game.dialogs
        dialogs.open("roster")
        roster = dialogs.active
        self.assertTrue(all(u.owner == "f0" for u in roster.units()))
        self.state.units["infantry0"].supplied = False
        roster.filter = "cut off"
        self.assertEqual([u.id for u in roster.units()], ["infantry0"])
        self.draw()
        self.click(roster.buttons["unit0"].center)
        self.assertIsNone(dialogs.mode)
        self.assertEqual(self.game.view.selected, "infantry0")


class StudyDialogTests(ScreenTestCase):
    scenario = DETAILED_SCENARIO

    def test_study_dialogs_render_and_capture_input(self):
        for mode in ("pedia", "strategy", "replay"):
            self.game.dialogs.open(mode)
            self.draw()
            self.assertIsNone(self.game.hit((400, 300)))
        self.game.dialogs.open("pedia")
        self.send(pygame.TEXTINPUT, text="supply")
        self.assertEqual(self.game.dialogs.active.query, "supply")
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(self.game.dialogs.mode)

    def test_regional_unit_page_is_illustrated(self):
        self.game.dialogs.open("pedia")
        pedia = self.game.dialogs.active
        pedia.section = "Units"
        pedia.query = "Yukon"
        self.assertTrue(pedia.results())
        self.draw()

    def test_replay_view_leaves_the_live_campaign_untouched(self):
        province = next(p.id for p in self.state.provinces.values() if p.controller == "f0")
        self.game.campaign.construct(province, "farm")
        before = digest(self.state)
        viewer = ReplayScreen(self.context, self.game, self.game.campaign.recorder.data())
        viewer.step()
        viewer.draw()
        self.assertEqual(digest(self.state), before)
        self.assertIsNot(viewer.playback.state, self.state)


if __name__ == "__main__":
    unittest.main()


class DiplomacyDialogTests(ScreenTestCase):
    def test_offer_peace_and_see_the_truce(self):
        self.key(pygame.K_d)
        self.assertEqual(self.game.dialogs.mode, "diplomacy")
        dialog = self.game.dialogs.active
        self.assertNotIn("f0", dialog.buttons)
        self.click(dialog.buttons["f1"].center)
        self.assertFalse(self.state.at_war("f0", "f1"))
        self.assertIn("Peace signed", dialog.notice)
        self.draw()
        self.click(dialog.buttons["f1"].center)  # Declaring war during the truce is refused.
        self.assertFalse(self.state.at_war("f0", "f1"))
