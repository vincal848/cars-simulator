import unittest
from copy import deepcopy

from cars.sim.air import coverage, mission, support_bonus_at
from cars.sim.combat import resolve
from cars.sim.entities import LAND_KINDS, Unit
from cars.sim.graph import Edge, Graph
from cars.sim.journal import record
from cars.sim.naval import reachable_seas
from cars.sim.orders import issue_move
from cars.sim.supply import refresh_supply
from cars.sim.turn import end_turn
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
        _, message = resolve(self.state, self.state.units["attack"], city, "cascadia", Edge())
        self.assertIn("artillery +25%", message)
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


class AirTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()
        self.air = self.state.units["air0"]
        self.air.remaining = self.air.allowance
        self.target = next(
            p for p in coverage(self.state, self.air) if p in self.state.provinces and p != self.air.location
        )
        self.state.units["target"] = Unit("target", "f1", self.target, defense=4)

    def test_coverage_depends_on_holding_the_base(self):
        self.assertIn("north_pacific", coverage(self.state, self.air))
        self.assertIn("canadian_shield", coverage(self.state, self.air))
        self.state.provinces["yukon"].controller = "f1"
        self.assertEqual(coverage(self.state, self.air), set())

    def test_strike_uses_the_single_sortie(self):
        origin = self.air.location
        self.assertTrue(mission(self.state, self.air.id, self.target, "strike")[0])
        self.assertEqual(self.air.location, origin)
        self.assertLess(self.state.units["target"].hp, 10)
        self.assertLess(self.air.hp, 10)
        snapshot = deepcopy(self.state.units)
        self.assertFalse(mission(self.state, self.air.id, self.target, "strike")[0])
        self.assertEqual(self.state.units, snapshot)
        self.assertEqual(self.state.reports[-1]["kind"], "air strike")

    def test_interceptors_spend_their_sortie(self):
        base = next(c.province for c in self.state.cities.values() if c.province != self.air.location)
        self.state.provinces[base].controller = "f1"
        self.state.air.connect(base, self.target)
        interceptor = Unit("interceptor", "f1", base, "air", attack=3)
        self.state.units[interceptor.id] = interceptor
        mission(self.state, self.air.id, self.target, "strike")
        self.assertEqual(interceptor.remaining, 0)
        self.assertIn("interceptors 1", self.state.reports[-1]["details"][0])

    def test_invalid_missions_change_nothing(self):
        before = deepcopy(self.state.units)
        self.assertFalse(mission(self.state, self.air.id, "missing", "strike")[0])
        self.assertFalse(mission(self.state, "target", self.target, "strike")[0])
        self.assertFalse(mission(self.state, self.air.id, self.air.location, "strike")[0])
        self.assertEqual(before, self.state.units)
        self.state.provinces[self.air.location].controller = "f1"
        self.assertFalse(mission(self.state, self.air.id, self.target, "strike")[0])

    def test_support_expires_and_rebase_needs_an_airbase(self):
        self.assertTrue(mission(self.state, self.air.id, self.target, "support")[0])
        self.assertEqual(support_bonus_at(self.state, "f0", self.target), 0.25)
        for _ in range(8):
            end_turn(self.state)
        self.assertEqual(support_bonus_at(self.state, "f0", self.target), 0)
        self.state.provinces[self.target].controller = "f0"
        self.state.provinces[self.target].buildings["airfield"] = 1
        self.assertTrue(mission(self.state, self.air.id, self.target, "rebase")[0])
        self.assertEqual(self.air.location, self.target)
        self.assertEqual(self.air.remaining, 0)

    def test_support_increases_land_damage(self):
        origin = self.air.location
        attacker = self.state.units["infantry0"]
        attacker.location = origin
        self.state.provinces[self.target].controller = "f1"
        baseline = deepcopy(self.state)
        mission(self.state, self.air.id, self.target, "support")
        resolve(self.state, attacker, origin, self.target, Edge())
        resolve(baseline, baseline.units[attacker.id], origin, self.target, Edge())

        def target_hp(state):
            return state.units["target"].hp if "target" in state.units else 0

        self.assertLess(target_hp(self.state), target_hp(baseline))


class JournalTests(unittest.TestCase):
    def test_journal_keeps_the_newest_entries(self):
        state, _, _ = compact()
        for i in range(200):
            record(state, "test", str(i))
        self.assertEqual(len(state.reports), 160)
        self.assertEqual(state.reports[0]["summary"], "40")


if __name__ == "__main__":
    unittest.main()
