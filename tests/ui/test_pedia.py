import unittest

import pygame

from cars.sim.nations import NATIONS
from cars.sim.recruitment import RECRUITS
from cars.sim.regional import CHARTERS
from cars.ui.pedia.library import LINK, PLACEHOLDER, build, fill, search
from tests.support import compact
from tests.ui.screen_case import ScreenTestCase


class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state, _, _ = compact()
        cls.library = build({f.id: f.name for f in state.factions.values()})

    def test_every_nation_unit_and_charter_has_an_article(self):
        for nation in NATIONS:
            self.assertIn("nation-" + nation, self.library)
        for kind in RECRUITS:
            self.assertIn("unit-" + kind, self.library)
        for charter in CHARTERS:
            self.assertIn("charter-" + charter, self.library)

    def test_rule_values_are_filled_in(self):
        for article in self.library.values():
            for text in article.body:
                self.assertIsNone(PLACEHOLDER.search(text), article.id)
        self.assertEqual(
            fill("{economy.occupied_yield:%} and ×{movement.terrain_cost.forest}"), "50% and ×1.4"
        )

    def test_links_all_lead_somewhere(self):
        for article in self.library.values():
            for text in article.body:
                for match in LINK.finditer(text):
                    self.assertIn(match.group(1), self.library)

    def test_search_puts_title_matches_first(self):
        results = search(self.library, "supply")
        self.assertEqual(results[0].id, "supply")
        self.assertEqual(search(self.library, "no such thing at all"), [])


class PediaWindowTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.game.open_pedia("combat")
        self.window = self.game.window

    def test_links_back_and_forward(self):
        self.click_area(self.window, "goto:forecast")
        self.assertEqual(self.window.current.id, "forecast")
        self.click_area(self.window, "back")
        self.assertEqual(self.window.current.id, "combat")
        self.click_area(self.window, "forward")
        self.assertEqual(self.window.current.id, "forecast")

    def test_typing_searches_and_enter_opens_the_first_result(self):
        for letter in "cavalry":
            self.send(pygame.TEXTINPUT, text=letter)
        self.draw()
        self.assertIsNotNone(self.window.area_of("goto:unit-cavalry"))
        self.key(pygame.K_RETURN)
        self.assertIn("cavalry", self.window.current.title.lower())

    def test_categories_fold(self):
        self.window.open_categories = set()
        self.click_area(self.window, "category:Units")
        self.assertIn("Units", self.window.open_categories)
        self.draw()
        self.assertIsNotNone(self.window.area_of("goto:unit-infantry"))

    def test_articles_with_plates_and_tables_draw(self):
        for article in ("unit-cavalry", "nation-f3", "traits", "building-roads", "terrain-mountains"):
            self.window.go(article)
            self.draw()


if __name__ == "__main__":
    unittest.main()
