import unittest

from cars.sim.entities import Unit
from cars.sim.visibility import can_see, visible_nodes
from tests.support import compact


class VisibilityTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()

    def test_own_territory_neighbours_and_ports_are_visible(self):
        seen = visible_nodes(self.state, "f0")
        for province in self.state.provinces.values():
            if province.controller == "f0":
                self.assertIn(province.id, seen)
                for neighbor, _ in self.state.land.neighbors(province.id):
                    self.assertIn(neighbor, seen)
        self.assertIn(self.state.ports["yukon"], seen)
        self.assertNotIn("tierra_del_fuego", seen)

    def test_units_extend_sight_around_them(self):
        self.assertNotIn("pampas", visible_nodes(self.state, "f0"))
        self.state.units["scout"] = Unit("scout", "f0", "la_plata", "scout")
        seen = visible_nodes(self.state, "f0")
        self.assertIn("la_plata", seen)
        self.assertTrue(any(neighbor in seen for neighbor, _ in self.state.land.neighbors("la_plata")))

    def test_hidden_enemies_but_never_own_units(self):
        own = Unit("own", "f0", "tierra_del_fuego")
        enemy = Unit("enemy", "f7", "tierra_del_fuego")
        seen = visible_nodes(self.state, "f0") - {"tierra_del_fuego"}
        self.assertTrue(can_see(own, "f0", seen))
        self.assertFalse(can_see(enemy, "f0", seen))
        self.assertTrue(can_see(enemy, "f0", None))


if __name__ == "__main__":
    unittest.main()
