import unittest

import pygame

from cars.persist.replay import digest
from cars.sim.balloons import coverage
from cars.sim.entities import Unit
from cars.sim.movement import reachable
from cars.sim.scenario import DETAILED_SCENARIO
from cars.ui.map.map_view import POLITICAL, SUPPLY
from cars.ui.screens.replay import ReplayScreen
from tests.ui.screen_case import ScreenTestCase


class OrdersTests(ScreenTestCase):
    def plate_of(self, unit_id: str):
        self.draw()
        return next(rect for rect, units in self.map.plates if unit_id in units)

    def test_select_a_plate_march_and_end_turn(self):
        self.click(self.plate_of("infantry0").center)
        self.assertEqual(self.game.view.selected, "infantry0")
        self.draw(hover="cascadia")
        self.click(self.map.anchors["cascadia"])
        self.assertEqual(self.state.units["infantry0"].location, "cascadia")
        self.assertIsNotNone(self.game.view.animation)
        self.game.update(1)
        self.assertIsNone(self.game.view.animation)
        self.key(pygame.K_SPACE)
        self.assertEqual(self.state.active, "f1")
        self.finish_rival_turns()
        self.assertEqual(self.state.round, 2)

    def test_dragging_pans_without_issuing_orders(self):
        before, offset = digest(self.state), list(self.map.camera.offset)
        self.press((500, 350))
        self.send(pygame.MOUSEMOTION, pos=(545, 380), rel=(45, 30), buttons=(1, 0, 0))
        self.send(pygame.MOUSEBUTTONUP, button=1, pos=(545, 380))
        self.assertNotEqual(offset, self.map.camera.offset)
        self.assertEqual(before, digest(self.state))
        self.assertIsNone(self.game.panel)

    def test_rival_turns_lock_orders_until_the_player_is_back(self):
        self.game.advance()
        active = self.state.active
        self.key(pygame.K_SPACE)
        self.assertEqual(self.state.active, active)
        self.finish_rival_turns(dt=0.4)

    def test_next_unit_skips_spent_units_and_centres_the_map(self):
        for unit in self.state.units.values():
            if unit.owner == "f0":
                unit.remaining = 0
        fleet = self.state.units["fleet0"]
        fleet.remaining = 1
        self.key(pygame.K_n)
        self.assertEqual(self.game.view.selected, fleet.id)
        self.assertEqual(self.game.view.layer, "naval")
        x, _ = self.map.camera.nearest(self.map.anchors[fleet.location])
        self.assertAlmostEqual(x, self.map.viewport.centerx, delta=2)
        fleet.remaining = 0
        self.game.next_ready()
        self.assertIn("spent", self.game.view.message)

    def test_tab_steps_through_a_stack(self):
        self.state.units["second"] = Unit("second", "f0", "yukon")
        self.game.select("infantry0")
        self.key(pygame.K_TAB)
        self.assertEqual(self.game.view.selected, "second")

    def test_balloon_missions_from_the_unit_card(self):
        corps = self.state.units["balloon0"]
        self.game.select(corps.id)
        self.draw()
        self.click(self.renderer.unit_card.mission_rect("relocate").center)
        self.assertEqual(self.game.view.mission_mode, "relocate")
        self.click(self.renderer.unit_card.mission_rect("observe").center)
        target = next(p for p in sorted(coverage(self.state, corps)) if p != corps.location)
        self.state.units["target"] = Unit("target", "f1", target)
        self.draw()
        self.click(self.map.anchors[target])
        self.assertEqual(self.state.units[corps.id].remaining, 0)
        self.assertEqual(self.state.ascents[-1]["target"], target)

    def test_right_click_opens_the_province_and_escape_backs_out(self):
        self.game.select("infantry0")
        self.press(self.map.anchors["yukon"], button=3)
        self.assertEqual(self.game.panel.name, "province")
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(self.game.panel)
        self.assertEqual(self.game.view.selected, "infantry0")
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(self.game.view.selected)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.window_name, "menu")

    def test_clicking_a_town_opens_its_province(self):
        self.draw()
        marker = next(m for m in self.map.city_markers if not self.renderer.blocks_map(m.rect.center))
        self.click(marker.rect.center)
        self.assertEqual(self.game.view.inspected, self.state.cities[marker.city].province)
        self.assertEqual(self.game.panel.name, "province")


class InterfaceTests(ScreenTestCase):
    def test_the_interface_keeps_clicks_off_the_map(self):
        self.draw()
        renderer = self.renderer
        for rect in (
            renderer.top_bar.rect,
            renderer.sidebar.rect,
            renderer.outliner.rect,
            renderer.controls.bar,
        ):
            self.assertIsNone(self.game.hit(rect.center))

    def test_the_side_bar_opens_and_closes_panels(self):
        self.draw()
        button = self.renderer.sidebar.buttons["military"]
        self.click(button.center)
        self.assertEqual(self.game.panel.name, "military")
        self.click(button.center)
        self.assertIsNone(self.game.panel)
        self.click(self.renderer.sidebar.buttons["pedia"].center)
        self.assertEqual(self.game.window_name, "pedia")

    def test_the_outliner_folds_sections_and_selects_units(self):
        self.draw()
        outliner = self.renderer.outliner
        fleets = next(rect for rect, action in outliner.areas if action == "toggle:fleets")
        self.click(fleets.center)
        self.assertTrue(outliner.open["fleets"])
        self.draw()
        row = next(rect for rect, action in outliner.areas if action == "unit:fleet0")
        self.click(row.center)
        self.assertEqual(self.game.view.selected, "fleet0")

    def test_map_modes_and_world_view(self):
        self.key(pygame.K_3)
        self.assertEqual(self.game.view.mode, SUPPLY)
        self.draw()
        self.click(self.renderer.controls.buttons[POLITICAL].center)
        self.assertEqual(self.game.view.mode, POLITICAL)
        self.map.zoom(3, (600, 400))
        self.click(self.renderer.controls.buttons["home"].center)
        self.assertAlmostEqual(self.map.camera.zoom_level, 1)

    def test_the_round_button_ends_the_turn(self):
        self.draw()
        self.click(self.renderer.controls.end_center)
        self.assertEqual(self.state.active, "f1")

    def test_the_date_opens_the_calendar(self):
        self.draw()
        self.click(self.renderer.top_bar.date_rect.center)
        self.assertEqual(self.game.window_name, "timeline")

    def test_messages_become_notifications(self):
        self.game.view.message = "Something happened."
        self.game.update(0.1)
        self.assertEqual(self.renderer.toasts.items[-1][0], "Something happened.")
        self.game.update(10)
        self.assertEqual(self.renderer.toasts.items, [])

    def test_the_hover_forecast_is_cached_until_the_state_changes(self):
        unit = self.state.units["infantry0"]
        unit.location = "canadian_shield"
        self.state.provinces["great_lakes"].controller = "f1"
        self.state.reindex_units()
        self.game.select(unit.id)
        self.context.pointer = self.map.anchors["great_lakes"]
        self.draw(hover="great_lakes")
        first = self.renderer.forecast.result
        self.assertIsNotNone(first)
        self.draw(hover="great_lakes")
        self.assertIs(self.renderer.forecast.result, first)
        unit.hp = 3
        self.draw(hover="great_lakes")
        self.assertIsNot(self.renderer.forecast.result, first)

    def test_the_interface_grows_with_the_scale(self):
        self.draw()
        height = self.renderer.top_bar.rect.height
        self.ui.set_scale(2.0)
        self.draw()
        self.assertEqual(self.renderer.top_bar.rect.height, height * 2)


class WindowSizeTests(unittest.TestCase):
    def test_every_part_fits_at_small_and_large_sizes(self):
        for size in ((1024, 700), (1920, 1080), (2560, 1440)):
            with self.subTest(size=size):
                case = ScreenTestCase()
                case.size = size
                case.setUp()
                try:
                    game = case.game
                    game.select("infantry0")
                    game.inspect("yukon")
                    case.draw()
                    renderer = game.renderer
                    self.assertFalse(renderer.unit_card.rect.colliderect(renderer.controls.rect))
                    self.assertFalse(renderer.outliner.rect.colliderect(renderer.controls.rect))
                    self.assertTrue(case.screen.get_rect().contains(game.panel.rect))
                    self.assertEqual(case.map.viewport, case.screen.get_rect())
                finally:
                    case.tearDown()


class PickerTests(ScreenTestCase):
    faction = None

    def test_the_picker_waits_for_a_nation(self):
        self.assertEqual(self.game.window_name, "picker")
        self.draw()
        self.assertIsNone(self.game.hit((600, 400)))
        self.key(pygame.K_3)
        picker = self.game.window
        self.assertEqual(picker.choice, "f2")
        self.click_area(picker, "choose:f4")
        self.assertEqual(picker.choice, "f4")
        self.click_area(picker, "start")
        self.assertEqual(self.game.campaign.player, "f4")
        self.assertIsNone(self.game.window)


class ReplayViewTests(ScreenTestCase):
    scenario = DETAILED_SCENARIO

    def test_the_replay_is_watched_without_touching_the_campaign(self):
        unit = next(u for u in self.state.units.values() if u.owner == "f0" and u.is_land)
        destination = next(p for p in reachable(self.state, unit).costs if p != unit.location)
        self.game.campaign.move(unit.id, destination)
        before = digest(self.state)
        viewer = ReplayScreen(self.context, self.game, self.game.campaign.recorder.data())
        self.game.viewer = viewer
        viewer.draw()
        self.assertFalse(viewer.renderer.interactive)
        viewer.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertEqual(viewer.playback.index, 1)
        viewer.draw()
        viewer.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=viewer.buttons["exit"].center))
        self.assertIsNone(self.game.viewer)
        self.assertEqual(before, digest(self.state))


if __name__ == "__main__":
    unittest.main()
