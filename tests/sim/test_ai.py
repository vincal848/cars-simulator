import unittest

from cars.sim.ai import RivalCommander
from cars.sim.entities import Unit
from cars.sim.movement import reachable
from tests.support import compact


class AttackJudgementTests(unittest.TestCase):
    """f1 attacks from the Great Lakes into f0's Canadian Shield."""

    def setUp(self):
        self.state, _, _ = compact()
        self.state.active_index = 1
        self.attacker = self.state.units["infantry1"]
        self.commander = RivalCommander(self.state)

    def worth_attacking(self) -> bool:
        route = reachable(self.state, self.attacker).path("canadian_shield")
        visible = self.commander._visible()
        return self.commander._worth_attacking(self.attacker, route, visible)

    def test_an_undefended_province_is_worth_taking(self):
        self.assertTrue(self.worth_attacking())

    def test_a_losing_attack_is_refused(self):
        self.state.units["guard"] = Unit("guard", "f0", "canadian_shield", hp=10, defense=8)
        self.attacker.hp = 3
        self.assertFalse(self.worth_attacking())

    def test_artillery_support_can_make_an_attack_worthwhile(self):
        self.state.units["guard"] = Unit("guard", "f0", "canadian_shield", hp=10, defense=9)
        self.assertFalse(self.worth_attacking())
        for index in range(2):
            self.state.units[f"gun{index}"] = Unit(f"gun{index}", "f1", "great_lakes", "artillery", attack=5)
        self.assertTrue(self.worth_attacking())


class FogTests(unittest.TestCase):
    def test_rivals_do_not_hunt_fleets_they_cannot_see(self):
        state, _, _ = compact()
        state.active_index = 3
        state.units["hunter"] = Unit("hunter", "f3", "north_atlantic", "fleet", allowance=8, remaining=8)
        commander = RivalCommander(state)
        self.assertNotIn("north_pacific", commander._visible())
        self.assertEqual(list(commander._hunt_fleets(state.units["hunter"])), [])
