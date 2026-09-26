import unittest

from tests.support import detailed


class DetailedScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state, cls.shapes, _ = detailed()

    def test_provinces_regions_and_islands(self):
        state = self.state
        self.assertEqual(len(state.provinces), 186)
        self.assertEqual(len(state.regions), 24)
        sizes = [len(state.land.reachable_from([p], lambda _: True)) for p in state.provinces]
        self.assertGreater(max(sizes), 90)
        self.assertIn(1, sizes)  # Islands get no artificial land edges.
        for unit in state.units.values():
            if unit.kind == "infantry":
                self.assertTrue(unit.supplied)
                self.assertGreater(len(state.land.adj[unit.location]), 0)

    def test_provinces_carry_real_geographic_names(self):
        for province in self.state.provinces.values():
            self.assertTrue(province.name)
            self.assertFalse(province.name[-1].isdigit())
            self.assertTrue(province.geography["admin"])
            self.assertTrue(province.geography["country"])
            self.assertEqual(province.geography["anchor"], self.shapes[province.shape_id]["anchor"])

    def test_cities_are_real_settlements(self):
        for city in self.state.cities.values():
            self.assertTrue(city.coordinates)
            self.assertEqual(city.location_source, "Natural Earth populated place")

    def test_city_style_survives_capture(self):
        city = next(iter(self.state.cities.values()))
        style = city.style
        self.state.provinces[city.province].controller = "f7"
        self.assertEqual(city.style, style)


if __name__ == "__main__":
    unittest.main()
