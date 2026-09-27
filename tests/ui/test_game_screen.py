import unittest
from unittest.mock import patch

import pygame

from cars.persist.replay import digest
from cars.sim.air import coverage
from cars.sim.entities import Unit
from cars.sim.movement import reachable
from cars.sim.scenario import DETAILED_SCENARIO
from cars.ui.map.map_view import Scene
from cars.ui.screens.game import FOCUS_POINT
from cars.ui.screens.replay import ReplayScreen
from tests.ui.screen_case import ScreenTestCase


class OrdersTests(ScreenTestCase):
    def test_select_move_animate_and_end_turn(self):
        self.click(self.map.anchors["yukon"])
        self.assertEqual(self.game.view.selected, "infantry0")
        self.draw(hover="cascadia")
        self.click(self.map.anchors["cascadia"])
        self.assertEqual(self.state.units["infantry0"].location, "cascadia")
        self.assertIsNotNone(self.game.view.animation)
        self.game.update(1)
        self.assertIsNone(self.game.view.animation)
        for layer in ("naval", "air", "supply"):
            self.game.switch_layer(layer)
            self.draw()
        self.key(pygame.K_SPACE)
        self.assertEqual(self.state.active, "f1")

    def test_dragging_pans_without_issuing_orders(self):
        before, offset = digest(self.state), list(self.map.camera.offset)
        self.press((500, 350))
        self.send(pygame.MOUSEMOTION, pos=(545, 380), rel=(45, 30), buttons=(1, 0, 0))
        self.send(pygame.MOUSEBUTTONUP, button=1, pos=(545, 380))
        self.assertNotEqual(offset, self.map.camera.offset)
        self.assertEqual(before, digest(self.state))
        self.assertFalse(self.renderer.province_window.is_open)

    def test_rival_turns_lock_input_until_the_player_is_back(self):
        self.game.advance()
        active = self.state.active
        self.key(pygame.K_SPACE)
        self.assertEqual(self.state.active, active)
        self.finish_rival_turns(dt=0.4)

    def test_next_ready_skips_spent_units_and_switches_layer(self):
        for unit in self.state.units.values():
            if unit.owner == "f0":
                unit.remaining = 0
        fleet = self.state.units["fleet0"]
        fleet.remaining = 1
        self.game.next_ready()
        self.assertEqual(self.game.view.selected, fleet.id)
        self.assertEqual(self.game.view.layer, "naval")
        self.assertAlmostEqual(
            self.map.camera.nearest(self.map.anchors[fleet.location])[0], FOCUS_POINT[0], delta=2
        )
        self.game.focus_unit("infantry1")
        self.assertEqual(self.game.view.selected, fleet.id)
        fleet.remaining = 0
        self.game.next_ready()
        self.assertIn("All units", self.game.view.message)

    def test_air_mission_buttons_and_group_cycling(self):
        game = self.game
        game.switch_layer("air")
        air = self.state.units[game.view.selected]
        target = next(p for p in coverage(self.state, air) if p in self.state.provinces and p != air.location)
        self.state.units["target"] = Unit("target", "f1", target)
        self.click(self.renderer.selection.air_buttons["strike"].center)
        with patch.object(self.renderer, "hit", return_value=target):
            self.click((500, 350))
        self.assertLess(self.state.units["target"].hp, 10)
        self.assertEqual(air.remaining, 0)
        self.state.units["secondair"] = Unit("secondair", "f0", air.location, "air")
        self.key(pygame.K_TAB)
        self.assertEqual(game.view.selected, "secondair")

    def test_recruiting_from_the_muster_tab_and_cycling_a_stack(self):
        self.state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
        city = self.state.units["infantry0"].location
        self.game.inspect(city, (10, 200))
        window = self.renderer.province_window
        self.click(window.tab_buttons["recruit"].center)
        self.click(window.recruit_buttons["artillery"].center)
        self.assertEqual(self.state.units[self.game.view.selected].kind, "artillery")
        self.draw()
        window.close()
        self.click(self.map.anchors[city])
        self.assertEqual(self.state.units[self.game.view.selected].kind, "infantry")


class ProvinceWindowTests(ScreenTestCase):
    scenario = DETAILED_SCENARIO

    def test_build_close_select_and_zoom(self):
        province = self.game.view.inspected
        controls = self.renderer.controls
        self.assertIsNone(self.game.hit(controls.end_button.center))
        for button in [controls.end_button, controls.home_button, *controls.view_buttons.values()]:
            self.assertTrue(controls.rect.contains(button))
        self.press(self.map.anchors[province], button=3)
        window = self.renderer.province_window
        self.assertTrue(window.is_open)
        self.click(window.build_buttons["farm"].center)
        self.assertEqual(self.state.provinces[province].buildings["farm"], 1)
        self.click(window.close_button.center)
        self.assertFalse(window.is_open)
        self.click(self.map.anchors[province])
        unit = self.state.units[self.game.view.selected]
        destination = next(p for p in reachable(self.state, unit).costs if p != province)
        self.draw(hover=destination)
        self.map.zoom(1.8, self.map.anchors[province])
        self.assertEqual(self.game.hit(self.map.anchors[province]), province)
        self.press(self.map.anchors[province], button=3)
        self.assertEqual(self.game.view.inspected, province)
        self.game.view.debug = True
        self.draw(hover=destination)

    def test_window_captures_input_and_stays_on_screen_when_dragged(self):
        province = self.game.view.inspected
        self.game.inspect(province, self.map.anchors[province])
        window = self.renderer.province_window
        self.assertIsNone(self.game.hit(window.rect.center))
        self.press(window.rect.center, button=3)
        self.assertEqual(self.game.view.inspected, province)
        self.press((window.rect.x + 30, window.rect.y + 20))
        self.send(pygame.MOUSEMOTION, rel=(2000, 2000), pos=(1199, 779))
        self.assertTrue(pygame.Rect(0, 44, 1200, 698).contains(window.rect))
        self.send(pygame.MOUSEBUTTONUP, button=1, pos=(1199, 779))
        self.key(pygame.K_ESCAPE)
        self.assertFalse(window.is_open)
        self.assertEqual(window.build_buttons, {})
        for layer, kind in (("naval", "fleet"), ("air", "air")):
            self.click(self.renderer.controls.view_buttons[layer].center)
            self.assertEqual(self.state.units[self.game.view.selected].kind, kind)
            self.draw()


class CityPinTests(ScreenTestCase):
    scenario = DETAILED_SCENARIO

    def test_city_pin_inspects_without_moving_the_selection(self):
        self.game.view.selected = next(u.id for u in self.state.units.values() if u.owner == "f0")
        before = {u.id: (u.location, u.remaining) for u in self.state.units.values()}
        marker = next(m for m in self.map.city_markers if not self.renderer.blocks_map(m.rect.center, "land"))
        self.assertAlmostEqual(marker.rect.centerx, marker.point[0], delta=1)
        self.assertAlmostEqual(marker.rect.centery, marker.point[1], delta=1)
        self.assertEqual(self.renderer.city_at(marker.rect.center, "land"), marker.city)
        self.click(marker.rect.center)
        self.assertEqual(self.game.view.inspected, self.state.cities[marker.city].province)
        self.assertTrue(self.renderer.province_window.is_open)
        self.assertEqual(before, {u.id: (u.location, u.remaining) for u in self.state.units.values()})
        self.draw()


class FactionPickerTests(ScreenTestCase):
    faction = None

    def test_picker_captures_input_until_a_faction_is_chosen(self):
        self.key(pygame.K_SPACE)
        self.assertIsNone(self.game.campaign.player)
        self.draw()
        self.click(self.renderer.picker.buttons["f2"].center)
        self.assertEqual(self.game.campaign.player, "f2")
        self.assertEqual(self.state.active, "f2")


class HudTests(ScreenTestCase):
    def test_menu_captures_clicks(self):
        menu = self.renderer.menu
        self.assertFalse(menu.open)
        self.click(menu.button.center)
        self.assertTrue(menu.open)
        save_button = menu.items["save"][0]
        self.assertTrue(self.renderer.blocks_map(save_button.center, "land"))
        font = self.context.theme.font_index
        self.click(menu.items["font"][0].center)
        self.assertNotEqual(self.context.theme.font_index, font)
        self.click(save_button.center)
        self.assertEqual(self.game.dialogs.mode, "save")
        self.assertFalse(menu.open)
        self.game.dialogs.close()
        self.click(menu.button.center)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(menu.open)

    def test_objectives_collapse_and_menu_display_toggle(self):
        objectives = self.renderer.objectives
        self.assertTrue(self.renderer.blocks_map(objectives.rect.center, "land"))
        self.click(objectives.button.center)
        self.assertTrue(objectives.collapsed)
        self.assertFalse(self.renderer.blocks_map(objectives.rect.center, "land"))
        self.click(self.renderer.menu.pedia_button.center)
        self.assertEqual(self.game.dialogs.mode, "pedia")
        self.game.dialogs.active.section = "History"
        self.click((800, 615))
        self.assertEqual(self.game.dialogs.mode, "reports")
        self.game.dialogs.close()
        self.click(self.renderer.menu.button.center)
        self.click(self.renderer.menu.items["display"][0].center)
        self.assertTrue(self.context.display_toggle_requested)
        self.assertFalse(self.renderer.menu.panel.colliderect(self.renderer.top_bar.date_rect))

    def test_f6_cycles_fonts(self):
        self.assertEqual(self.context.theme.font_index, 1)
        self.key(pygame.K_F6)
        self.assertEqual(self.context.theme.font_index, 2)

    def test_hover_forecast_is_cached_until_the_state_changes(self):
        unit = self.state.units["infantry0"]
        unit.location = "canadian_shield"
        unit.remaining = 20
        self.game.view.selected = unit.id
        target = next(
            p for p in self.state.land.adj[unit.location] if self.state.provinces[p].controller != "f0"
        )
        self.context.pointer = (420, 300)
        card = self.renderer.forecast
        self.draw(hover=target)
        first = card.result
        self.draw(hover=target)
        self.assertIs(first, card.result)
        unit.hp -= 1
        self.draw(hover=target)
        self.assertIsNot(first, card.result)


if __name__ == "__main__":
    unittest.main()


class FogOfWarTests(ScreenTestCase):
    def shown(self) -> set[str]:
        scene = Scene(layer="land", viewer="f0", visible=self.renderer.visible(self.game.view))
        return {unit.id for unit in self.map.visible_units(scene)}

    def test_distant_enemies_are_hidden_until_debug_reveals_them(self):
        self.assertIn("infantry0", self.shown())
        self.assertNotIn("infantry7", self.shown())  # In Pampas, far from the Northern Union.
        self.game.view.debug = True
        self.assertIn("infantry7", self.shown())

    def test_replays_are_watched_without_fog(self):
        viewer = ReplayScreen(self.context, self.game, self.game.campaign.recorder.data())
        self.assertIsNone(viewer.renderer.visible(viewer.view))
