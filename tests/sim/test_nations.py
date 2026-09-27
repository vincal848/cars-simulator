import unittest

from cars.sim.combat import assess
from cars.sim.economy import forecast, storage
from cars.sim.entities import Unit
from cars.sim.graph import Edge
from cars.sim.market import treasury_income
from cars.sim.movement import movement_cost
from cars.sim.nations import NATIONS, modifier
from cars.sim.recruitment import RECRUITS, quote_recruit
from tests.support import compact


class NationTests(unittest.TestCase):
    def test_every_nation_has_a_history_and_two_traits(self):
        self.assertEqual(len(NATIONS), 8)
        for nation in NATIONS.values():
            self.assertGreaterEqual(len(nation.history), 2)
            self.assertEqual(len(nation.traits), 2)

    def test_modifiers_multiply_and_amounts_add(self):
        self.assertEqual(modifier("f3", "recruit_cost", "fleet"), 0.75)
        self.assertEqual(modifier("f3", "recruit_cost", "infantry"), 1)
        self.assertEqual(modifier("f1", "gold_income", default=0), 3)
        self.assertEqual(modifier("nobody", "attack", "infantry"), 1)


class TraitEffectTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()

    def test_cheaper_recruitment(self):
        self.state.active_index = 3  # British North America: the Royal Navy's fleets are a quarter cheaper.
        city = next(
            c for c in self.state.cities.values() if self.state.provinces[c.province].controller == "f3"
        )
        expected = {resource: round(amount * 0.75) for resource, amount in RECRUITS["fleet"]["cost"].items()}
        self.assertEqual(quote_recruit(self.state, city.province, "fleet")[0], expected)

    def test_attack_and_defence(self):
        state = self.state
        state.provinces["canadian_shield"].controller = "f4"
        state.provinces["canadian_shield"].terrain = "mountains"
        attacker = Unit("a", "f1", "great_lakes")  # Mexico: infantry +10%.
        defender = Unit("d", "f4", "canadian_shield")  # New Granada: +20% in mountains.
        plain = Unit("p", "f2", "canadian_shield")
        odds = assess(state, attacker, "great_lakes", "canadian_shield", Edge(), [defender])
        baseline = assess(state, attacker, "great_lakes", "canadian_shield", Edge(), [plain])
        self.assertAlmostEqual(odds.strength, attacker.attack_power() * 1.1)
        self.assertAlmostEqual(odds.defense, baseline.defense * 1.2)

    def test_movement_production_storage_and_gold(self):
        state = self.state
        unit = Unit("u", "f6", "yukon")  # Brazil: 20% cheaper through forest.
        state.provinces["cascadia"].terrain = "forest"
        state.provinces["cascadia"].controller = "f6"
        forest = movement_cost("yukon", "cascadia", Edge(), unit, state, set())
        unit.owner = "f2"
        state.provinces["cascadia"].controller = "f2"
        self.assertAlmostEqual(forest, movement_cost("yukon", "cascadia", Edge(), unit, state, set()) * 0.8)
        self.assertEqual(storage(state, "f7"), storage(state, "f6"))
        self.assertEqual(treasury_income(state, "f1") - treasury_income(state, "f2"), 3)
        self.assertGreater(forecast(state, "f5")["food"], 0)
