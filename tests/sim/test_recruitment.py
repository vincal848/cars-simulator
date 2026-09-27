import unittest

from cars.sim.balloons import coverage
from cars.sim.buildings import build
from cars.sim.economy import forecast
from cars.sim.graph import Edge
from cars.sim.movement import movement_cost
from cars.sim.recruitment import RECRUITS, quote_recruit, recruit
from cars.sim.regional import CHARTERS, charter_for
from cars.sim.turn import end_turn
from tests.support import compact, detailed


class CityRecruitmentTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()
        self.state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
        self.city = self.state.units["infantry0"].location

    def test_cost_one_per_city_and_ready_next_turn(self):
        before = self.state.factions["f0"].resources.copy()
        unit_id, _ = recruit(self.state, self.city, "cavalry")
        self.assertIsNotNone(unit_id)
        self.assertEqual(self.state.units[unit_id].remaining, 0)
        self.assertIn(unit_id, self.state.provinces[self.city].units)
        for resource, cost in RECRUITS["cavalry"]["cost"].items():
            self.assertEqual(self.state.factions["f0"].resources[resource], before[resource] - cost)
        self.assertIsNone(recruit(self.state, self.city, "scout")[0])
        for _ in range(8):
            end_turn(self.state)
        self.assertEqual(self.state.units[unit_id].remaining, 8)
        self.assertIsNotNone(recruit(self.state, self.city, "artillery")[0])

    def test_invalid_recruitment_changes_nothing(self):
        before = self.state.factions["f0"].resources.copy()
        enemy = next(p.id for p in self.state.provinces.values() if p.controller == "f1")
        for province, kind in ((enemy, "scout"), (self.city, "fleet"), ("missing", "infantry")):
            self.assertIsNone(recruit(self.state, province, kind)[0])
        self.assertEqual(before, self.state.factions["f0"].resources)


class ServiceRecruitmentTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = detailed()
        self.state.factions["f0"].resources = dict(wood=1000, food=1000, iron=1000)
        self.port = next(
            c.province
            for c in self.state.cities.values()
            if self.state.provinces[c.province].controller == "f0" and c.province in self.state.ports
        )

    def test_fleets_need_a_shipyard(self):
        state = self.state
        self.assertIsNone(recruit(state, self.port, "fleet")[0])
        before = forecast(state, "f0")
        self.assertTrue(build(state, self.port, "shipyard")[0])
        self.assertFalse(build(state, self.port, "shipyard")[0])
        self.assertEqual(before, forecast(state, "f0"))
        unit_id, _ = recruit(state, self.port, "fleet")
        self.assertIsNotNone(unit_id)
        self.assertEqual(state.units[unit_id].location, state.ports[self.port])
        self.assertEqual(state.units[unit_id].remaining, 0)
        self.assertIsNone(recruit(state, self.port, "infantry")[0])

    def test_balloon_corps_need_gas_works_and_lose_range_with_their_post(self):
        state = self.state
        self.assertIsNone(recruit(state, self.port, "balloon")[0])
        self.assertTrue(build(state, self.port, "gasworks")[0])
        unit_id, _ = recruit(state, self.port, "balloon")
        self.assertIn(self.port, coverage(state, state.units[unit_id]))
        state.provinces[self.port].controller = "f1"
        self.assertFalse(coverage(state, state.units[unit_id]))


class RegionalCharterTests(unittest.TestCase):
    def test_every_region_offers_a_charter_with_a_terrain_specialty(self):
        state, _, _ = detailed()
        self.assertEqual(set(CHARTERS), set(state.regions))
        for region_id, charter in CHARTERS.items():
            city = next(
                c for c in state.cities.values() if state.provinces[c.province].region_id == region_id
            )
            province = state.provinces[city.province]
            province.controller = "f0"
            state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
            unit_id, message = recruit(state, province.id, "regional")
            self.assertIsNotNone(unit_id, message)
            unit = state.units[unit_id]
            self.assertEqual(unit.regional, region_id)
            self.assertEqual(unit.kind, charter.kind)
            province.terrain = charter.terrain
            unit.supplied = True
            special = movement_cost(province.id, province.id, Edge(), unit, state, set())
            unit.regional = ""
            normal = movement_cost(province.id, province.id, Edge(), unit, state, set())
            unit.regional = region_id
            self.assertAlmostEqual(special, normal * 0.8)
            # Each city recruits once per turn.
            self.assertTrue(quote_recruit(state, province.id, "regional")[1])

    def test_compact_scenario_matches_charters_by_region_name(self):
        state, _, _ = compact()
        for province in state.provinces:
            charter = charter_for(state, province)
            self.assertIsNotNone(charter)
            self.assertEqual(charter.region, state.regions[state.provinces[province].region_id].name)


if __name__ == "__main__":
    unittest.main()
