import unittest

from cars.sim.ai import faction_actions
from cars.sim.economy import forecast
from cars.sim.entities import Unit
from cars.sim.turn import end_turn
from cars.sim.upkeep import net_income, pay_upkeep, upkeep
from tests.support import compact


class UpkeepTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()
        self.stock = self.state.factions["f0"].resources

    def test_each_unit_costs_its_upkeep(self):
        # f0 starts with one infantry regiment, one fleet and one air group, and its
        # Long Winters trait cuts food upkeep by a fifth.
        self.assertEqual(upkeep(self.state, "f0"), dict(wood=1, food=0.8, iron=1))
        income = net_income(self.state, "f0")
        gross = forecast(self.state, "f0")
        self.assertAlmostEqual(income["food"], gross["food"] - 0.8)

    def test_upkeep_is_paid_after_production(self):
        before = dict(self.stock)
        gains = forecast(self.state, "f0")
        end_turn(self.state)
        for resource, amount in upkeep(self.state, "f0").items():
            self.assertAlmostEqual(self.stock[resource], before[resource] + gains[resource] - amount)

    def test_a_shortfall_costs_the_units_that_needed_it(self):
        self.stock.update(wood=10, food=0, iron=10)
        infantry, fleet = self.state.units["infantry0"], self.state.units["fleet0"]
        self.assertEqual(pay_upkeep(self.state, "f0"), ["food"])
        self.assertEqual(self.stock["food"], 0)
        self.assertEqual(infantry.hp, 9)
        self.assertEqual(fleet.hp, 10)
        self.assertEqual(self.state.reports[-1]["kind"], "upkeep")

    def test_starving_units_disband(self):
        self.stock["food"] = 0
        infantry = self.state.units["infantry0"]
        infantry.hp = 0.5
        pay_upkeep(self.state, "f0")
        self.assertNotIn(infantry.id, self.state.units)
        self.assertNotIn(infantry.id, self.state.provinces[infantry.location].units)
        self.assertIn("infantry0: disbanded", self.state.reports[-1]["details"])

    def test_rivals_only_recruit_what_they_can_feed(self):
        state = self.state
        state.factions["f0"].resources = dict(wood=500, food=500, iron=500)
        for i in range(30):
            state.units[f"extra{i}"] = Unit(f"extra{i}", "f0", "yukon")
        state.reindex_units()
        self.assertLess(net_income(state, "f0")["food"], 0)
        list(faction_actions(state))
        self.assertFalse(any(report["kind"] == "recruitment" for report in state.reports))


if __name__ == "__main__":
    unittest.main()
