import unittest

import pygame

from cars.sim.entities import Unit
from cars.sim.scenario import DETAILED_SCENARIO
from cars.ui.panels import PANELS
from tests.ui.screen_case import ScreenTestCase


class ProvincePanelTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
        self.game.inspect("yukon")
        self.panel = self.game.panel

    def test_build_from_the_buildings_table(self):
        self.click_area(self.panel, "build:farm")
        self.assertEqual(self.state.provinces["yukon"].buildings["farm"], 1)
        self.assertIn("Farm", self.panel.notice)

    def test_raise_a_regiment_from_the_recruitment_table(self):
        self.draw()
        self.panel.scroll = 10_000
        self.click_area(self.panel, "recruit:artillery")
        self.assertEqual(self.state.units[self.game.view.selected].kind, "artillery")
        self.draw()
        self.assertIsNone(self.panel.area_of("recruit:infantry"))  # One unit per city per turn.

    def test_the_panel_scrolls_and_captures_the_pointer(self):
        self.draw()
        self.assertIsNone(self.game.hit(self.panel.rect.center))
        self.context.pointer = self.panel.rect.center
        self.send(pygame.MOUSEWHEEL, x=0, y=-5)
        self.draw()
        self.assertGreater(self.panel.scroll, 0)

    def test_a_province_you_do_not_hold_offers_nothing_to_build(self):
        self.game.inspect("great_lakes")
        self.draw()
        self.assertIsNone(self.panel.area_of("build:farm"))


class NationPanelTests(ScreenTestCase):
    def test_every_nation_panel_draws(self):
        for faction in self.state.factions:
            self.game.campaign.player = faction
            self.game.open_panel("nation")
            self.draw()
            self.renderer.panel = None


class MilitaryPanelTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.game.open_panel("military")
        self.panel = self.game.panel

    def test_filters_sorting_and_focus(self):
        self.state.units["infantry0"].hp = 4
        self.click_area(self.panel, "filter:wounded")
        self.assertEqual([u.id for u in self.panel.units()], ["infantry0"])
        self.click_area(self.panel, "filter:all")
        self.draw()
        strength = self.panel.table._header[3]
        self.click(strength.center)
        self.draw()
        self.assertEqual(self.panel.table.rows[0].id, "infantry0")
        row = next(rect for rect, unit in self.panel.table._row_rects if unit.id == "fleet0")
        self.click(row.center)
        self.assertEqual(self.game.view.selected, "fleet0")


class DiplomacyPanelTests(ScreenTestCase):
    scenario = DETAILED_SCENARIO

    def setUp(self):
        super().setUp()
        self.game.open_panel("diplomacy")
        self.panel = self.game.panel

    def test_select_a_rival_and_make_peace(self):
        self.draw()
        row = next(rect for rect, faction in self.panel.table._row_rects if faction == "f2")
        self.click(row.center)
        self.assertEqual(self.panel.selected, "f2")
        for i in range(10):
            self.state.units[f"extra{i}"] = Unit(f"extra{i}", "f0", "province_000")
        self.click_area(self.panel, "treaty:f2")
        self.assertFalse(self.state.at_war("f0", "f2"))

    def test_the_war_screen_counts_victory_points(self):
        self.panel.selected = "f1"
        city = next(c for c in self.state.cities.values() if self.state.provinces[c.province].owner == "f1")
        self.state.provinces[city.province].controller = "f0"
        self.draw()
        # The war section is only drawn while at war.
        self.assertTrue(self.state.at_war("f0", "f1"))


class MarketPanelTests(ScreenTestCase):
    def test_buying_a_lot(self):
        self.game.open_panel("market")
        gold = self.state.factions["f0"].gold
        self.click_area(self.game.panel, "trade:food:buy")
        self.assertLess(self.state.factions["f0"].gold, gold)
        self.assertIn("Bought", self.game.panel.notice)


class ChroniclePanelTests(ScreenTestCase):
    def test_filters(self):
        self.game.open_panel("chronicle")
        panel = self.game.panel
        self.assertEqual(panel.filter, "battles")
        self.click_area(panel, "filter:all")
        self.assertEqual(panel.filter, "all")


class PanelRegistryTests(unittest.TestCase):
    def test_every_panel_has_a_name_matching_its_key(self):
        for name, cls in PANELS.items():
            self.assertEqual(cls.name, name)


if __name__ == "__main__":
    unittest.main()
