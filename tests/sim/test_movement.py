import unittest
from itertools import pairwise
from math import inf

from cars.sim.buildings import build
from cars.sim.entities import Unit
from cars.sim.graph import Edge
from cars.sim.movement import hostile_zoc, movement_cost, reachable
from cars.sim.supply import refresh_supply, supplied_provinces, supply_route
from tests.support import compact, detailed


class MovementCostTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()
        self.unit = self.state.units["infantry0"]

    def cost(self, edge=None, destination="cascadia"):
        return movement_cost("yukon", destination, edge or Edge(), self.unit, self.state, set())

    def test_terrain_river_roads_and_supply_compose(self):
        province = self.state.provinces["cascadia"]
        province.terrain = "plains"
        plain = self.cost()
        province.terrain = "mountains"
        mountain = self.cost()
        self.assertGreater(mountain, plain)
        self.assertAlmostEqual(self.cost(Edge(river_crossing="test")), mountain + 1)
        self.assertLess(self.cost(Edge(infrastructure=2)), mountain)
        self.unit.supplied = False
        self.assertAlmostEqual(self.cost(), mountain * 1.5)

    def test_only_enemies_in_sight_exert_a_zone_of_control(self):
        self.state.units["hidden"] = Unit("hidden", "f7", "tierra_del_fuego")
        zoc = hostile_zoc(self.state, "f0")
        self.assertNotIn("pampas", zoc)
        self.state.units["scout"] = Unit("scout", "f0", "austral_andes", "scout")
        self.assertIn("pampas", hostile_zoc(self.state, "f0"))

    def test_closed_border_is_impassable(self):
        self.assertEqual(
            movement_cost("yukon", "cascadia", Edge(border_type="closed"), self.unit, self.state), inf
        )

    def test_zone_of_control_and_hostile_ground_ends_route(self):
        self.assertIn("canadian_shield", hostile_zoc(self.state, "f0"))
        edge = self.state.land.edge("yukon", "canadian_shield")
        base = movement_cost("yukon", "canadian_shield", edge, self.unit, self.state, set())
        self.assertAlmostEqual(
            movement_cost("yukon", "canadian_shield", edge, self.unit, self.state), base + 1
        )
        self.unit.remaining = 100
        paths = reachable(self.state, self.unit)
        self.assertIn("great_lakes", paths.costs)
        self.assertNotIn("appalachia", paths.costs)

    def test_role_specific_terrain_costs(self):
        city = self.unit.location
        province = self.state.provinces[city]

        def cost(kind):
            return movement_cost(city, city, Edge(), Unit("x", "f0", city, kind), self.state, zoc=set())

        province.terrain = "plains"
        self.assertLess(cost("cavalry"), cost("infantry"))
        province.terrain = "mountains"
        self.assertLess(cost("scout"), cost("infantry"))
        self.assertGreater(cost("cavalry"), cost("infantry"))
        self.assertGreater(cost("artillery"), cost("cavalry"))


class RoadTests(unittest.TestCase):
    def test_roads_discount_terrain_without_erasing_river(self):
        state, _, _ = detailed()
        state.factions["f0"].resources = dict(wood=1000, food=1000, iron=1000)
        unit = next(u for u in state.units.values() if u.kind == "infantry")
        unit.supplied = True
        province = next(p for p in state.provinces.values() if p.controller == "f0")
        province.terrain = "plains"
        edge = Edge(base_cost=2, river_crossing="test")
        baseline = movement_cost(unit.location, province.id, edge, unit, state, set())
        for level in range(1, 4):
            self.assertTrue(build(state, province.id, "roads")[0])
            self.assertAlmostEqual(
                movement_cost(unit.location, province.id, edge, unit, state, set()), baseline - 0.1 * level
            )
        self.assertFalse(build(state, province.id, "roads")[0])


class SupplyTests(unittest.TestCase):
    def test_losing_a_connecting_province_cuts_supply(self):
        state, _, _ = compact()
        unit = state.units["infantry0"]
        unit.location = "cascadia"
        refresh_supply(state)
        self.assertTrue(unit.supplied)
        state.provinces["yukon"].controller = "f1"
        refresh_supply(state)
        self.assertFalse(unit.supplied)

    def test_routes_match_connectivity(self):
        state, _, _ = compact()
        for owner in state.factions:
            connected = supplied_provinces(state, owner)
            for province in state.provinces:
                route = supply_route(state, owner, province)
                self.assertEqual(bool(route), province in connected)
                for a, b in pairwise(route):
                    self.assertIn(b, state.supply.adj[a])
                    self.assertEqual(state.provinces[b].controller, owner)
        for city in state.cities.values():
            city.supply_hub = False
        self.assertEqual(supply_route(state, "f0", state.units["infantry0"].location), [])


if __name__ == "__main__":
    unittest.main()
