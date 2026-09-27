import unittest
from copy import deepcopy

from cars.sim.balloons import coverage, mission, spotting_at
from cars.sim.combat import resolve
from cars.sim.entities import LAND_KINDS, Unit
from cars.sim.graph import Edge, Graph
from cars.sim.journal import record
from cars.sim.naval import reachable_seas
from cars.sim.orders import issue_move
from cars.sim.supply import refresh_supply
from cars.sim.turn import end_turn
from cars.sim.visibility import visible_nodes
from tests.support import compact


class LandOrderTests(unittest.TestCase):
    def setUp(self):
        self.state, self.shapes, _ = compact()
        self.unit = self.state.units["infantry0"]

    def test_scenario_loads_consistently(self):
        state = self.state
        self.assertEqual(len(state.factions), 8)
        self.assertEqual(len(state.provinces), 24)
        self.assertEqual(set(state.land.adj), set(self.shapes))
        self.assertIsNot(state.land, state.supply)
        for province in state.provinces.values():
            self.assertIn(province.id, state.regions[province.region_id].provinces)

    def test_capture_changes_control_but_not_ownership(self):
        route, _ = issue_move(self.state, self.unit.id, "cascadia")
        self.assertEqual(route, ["yukon", "cascadia"])
        self.assertIn(self.unit.id, self.state.provinces["cascadia"].units)
        self.unit.remaining = 10
        issue_move(self.state, self.unit.id, "great_basin")
        self.assertEqual(self.state.provinces["great_basin"].controller, "f0")
        self.assertEqual(self.state.provinces["great_basin"].owner, "f1")
        self.assertEqual(self.unit.remaining, 0)

    def test_illegal_orders_change_nothing(self):
        before = self.unit.remaining
        self.assertEqual(issue_move(self.state, "infantry1", "canadian_shield")[0], [])
        self.assertEqual(issue_move(self.state, self.unit.id, "pampas")[0], [])
        self.assertEqual(before, self.unit.remaining)

    def test_repelled_attack_costs_both_sides(self):
        self.unit.location = "canadian_shield"
        self.unit.remaining = 10
        defender = self.state.units["infantry1"]
        issue_move(self.state, self.unit.id, "great_lakes")
        self.assertEqual(self.unit.location, "canadian_shield")
        self.assertLess(defender.hp, 10)
        self.assertLess(self.unit.hp, 10)
        self.assertEqual(self.unit.remaining, 0)

    def test_every_land_role_moves_along_supplied_land_paths(self):
        for kind in LAND_KINDS:
            with self.subTest(kind=kind):
                state, _, _ = compact()
                unit = state.units["infantry0"]
                unit.kind = kind
                refresh_supply(state)
                self.assertTrue(unit.supplied)
                route, _ = issue_move(state, unit.id, "cascadia")
                self.assertGreater(len(route), 1)
                self.assertIn(unit.id, state.provinces["cascadia"].units)

    def test_artillery_support_is_committed_and_new_roles_defend(self):
        city = self.unit.location
        self.state.provinces["cascadia"].controller = "f1"
        self.state.units = {
            "attack": Unit("attack", "f0", city),
            "gun": Unit("gun", "f0", city, "artillery"),
            "defense": Unit("defense", "f1", "cascadia", "cavalry", hp=100),
        }
        resolve(self.state, self.state.units["attack"], city, "cascadia", Edge())
        self.assertIn(["Artillery support", "+25%"], self.state.reports[-1]["factors"])
        self.assertEqual(self.state.units["gun"].remaining, 0)
        self.assertEqual(self.state.provinces["cascadia"].controller, "f1")


class NavalTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()

    def fleets(self):
        self.state.naval = Graph()
        self.state.naval.connect("a", "b")
        self.state.naval.connect("b", "c")
        self.state.units = {
            "a": Unit("a", "f0", "a", "fleet", remaining=6, attack=5),
            "b": Unit("b", "f1", "b", "fleet", hp=10, defense=3),
        }
        return self.state.units["a"]

    def test_bundled_fleet_can_sail(self):
        fleet = self.state.units["fleet0"]
        self.assertIn("south_pacific", reachable_seas(self.state, fleet).costs)
        route, _ = issue_move(self.state, "fleet0", "south_pacific")
        self.assertEqual(route, ["north_pacific", "south_pacific"])

    def test_enemy_fleets_end_routes_and_take_losses(self):
        fleet = self.fleets()
        self.assertNotIn("c", reachable_seas(self.state, fleet).costs)
        route, _ = issue_move(self.state, fleet.id, "b")
        self.assertEqual(route, ["a"])
        self.assertEqual(fleet.remaining, 0)
        self.assertLess(self.state.units["b"].hp, 10)
        report = self.state.reports[-1]
        self.assertEqual(report["kind"], "naval battle")
        self.assertIn("f1", report["participants"])
        self.assertTrue(report["details"])

    def test_victory_and_destruction(self):
        self.fleets()
        self.state.units["b"].hp = 1
        self.assertEqual(issue_move(self.state, "a", "b")[0], ["a", "b"])
        self.assertNotIn("b", self.state.units)
        fleet = self.fleets()
        fleet.hp = 0.2
        issue_move(self.state, "a", "b")
        self.assertNotIn("a", self.state.units)

    def test_same_sea_combat_and_foreign_orders(self):
        fleet = self.fleets()
        fleet.location = "b"
        self.assertEqual(issue_move(self.state, "b", "a")[0], [])
        self.assertEqual(issue_move(self.state, "a", "b")[0], ["b"])
        self.assertLess(fleet.hp, 10)


class BalloonTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()
        self.corps = self.state.units["balloon0"]
        self.corps.remaining = self.corps.allowance
        self.target = next(p for p in sorted(coverage(self.state, self.corps)) if p != self.corps.location)
        self.state.units["target"] = Unit("target", "f1", self.target, defense=4)
        self.state.reindex_units()

    def test_range_depends_on_holding_the_post(self):
        self.assertIn("canadian_shield", coverage(self.state, self.corps))
        self.assertNotIn("north_pacific", coverage(self.state, self.corps))
        self.state.provinces["yukon"].controller = "f1"
        self.assertEqual(coverage(self.state, self.corps), set())

    def test_an_ascent_reveals_the_province_and_its_neighbours(self):
        before = visible_nodes(self.state, "f0")
        self.assertTrue(mission(self.state, self.corps.id, self.target, "observe")[0])
        seen = visible_nodes(self.state, "f0")
        self.assertLessEqual(before, seen)
        self.assertIn(self.target, seen)
        for neighbor, _ in self.state.land.neighbors(self.target):
            self.assertIn(neighbor, seen)
        self.assertEqual(self.state.reports[-1]["kind"], "ascent")

    def test_one_ascent_a_turn(self):
        self.assertTrue(mission(self.state, self.corps.id, self.target, "observe")[0])
        snapshot = deepcopy(self.state.units)
        self.assertFalse(mission(self.state, self.corps.id, self.target, "observe")[0])
        self.assertEqual(self.state.units, snapshot)

    def test_invalid_missions_change_nothing(self):
        before = deepcopy(self.state.units)
        self.assertFalse(mission(self.state, self.corps.id, "missing", "observe")[0])
        self.assertFalse(mission(self.state, "target", self.target, "observe")[0])
        self.assertFalse(mission(self.state, self.corps.id, self.target, "strike")[0])
        self.assertEqual(before, self.state.units)
        self.state.provinces[self.corps.location].controller = "f1"
        self.assertFalse(mission(self.state, self.corps.id, self.target, "observe")[0])

    def test_observation_expires_and_relocation_needs_control(self):
        self.assertTrue(mission(self.state, self.corps.id, self.target, "observe")[0])
        self.assertEqual(spotting_at(self.state, "f0", self.target), 0.5)
        for _ in range(8):
            end_turn(self.state)
        self.assertEqual(spotting_at(self.state, "f0", self.target), 0)
        self.state.provinces[self.target].controller = "f1"
        self.assertFalse(mission(self.state, self.corps.id, self.target, "relocate")[0])
        self.state.provinces[self.target].controller = "f0"
        self.assertTrue(mission(self.state, self.corps.id, self.target, "relocate")[0])
        self.assertEqual(self.corps.location, self.target)
        self.assertEqual(self.corps.remaining, 0)

    def test_spotting_strengthens_artillery_only(self):
        origin = self.corps.location
        attacker = self.state.units["infantry0"]
        attacker.location = origin
        self.state.provinces[self.target].controller = "f1"

        def attack(with_guns: bool, spotted: bool) -> float:
            state = deepcopy(self.state)
            if with_guns:
                state.units["gun"] = Unit("gun", "f0", origin, "artillery")
            if spotted:
                mission(state, "balloon0", self.target, "observe")
            resolve(state, state.units[attacker.id], origin, self.target, Edge())
            return state.units["target"].hp if "target" in state.units else 0

        self.assertEqual(attack(False, True), attack(False, False))
        self.assertLess(attack(True, True), attack(True, False))

    def test_a_captured_post_takes_the_corps_with_it(self):
        self.state.units["raider"] = Unit("raider", "f1", self.target, attack=100)
        self.state.provinces[self.corps.location].controller = "f0"
        for unit_id in [u for u, unit in self.state.units.items() if unit.location == self.corps.location]:
            if self.state.units[unit_id].is_land:
                del self.state.units[unit_id]
        self.state.active_index = 1
        self.state.reindex_units()
        resolve(self.state, self.state.units["raider"], self.target, self.corps.location, Edge())
        self.assertNotIn("balloon0", self.state.units)


class JournalTests(unittest.TestCase):
    def test_journal_keeps_the_newest_entries(self):
        state, _, _ = compact()
        for i in range(200):
            record(state, "test", str(i))
        self.assertEqual(len(state.reports), 160)
        self.assertEqual(state.reports[0]["summary"], "40")


if __name__ == "__main__":
    unittest.main()
