import unittest

from cars.sim.entities import FULL_STRENGTH, Unit
from cars.sim.recovery import recover, recovery_rate
from cars.sim.supply import refresh_supply
from cars.sim.turn import end_turn
from tests.support import compact


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()
        self.unit = self.state.units["infantry0"]  # In Yukon, a friendly city.

    def test_supplied_units_recover_faster_in_a_city(self):
        self.unit.hp = 5
        recover(self.state, "f0")
        self.assertEqual(self.unit.hp, 7)
        self.unit.location = "cascadia"  # Friendly, supplied, no city.
        self.state.reindex_units()
        recover(self.state, "f0")
        self.assertEqual(self.unit.hp, 8)

    def test_recovery_never_exceeds_full_strength(self):
        self.unit.hp = FULL_STRENGTH - 0.5
        recover(self.state, "f0")
        self.assertEqual(self.unit.hp, FULL_STRENGTH)

    def test_no_recovery_when_cut_off_or_on_enemy_ground(self):
        self.unit.hp = 5
        self.state.provinces["yukon"].controller = "f1"
        refresh_supply(self.state)
        self.assertEqual(recovery_rate(self.state, self.unit), 0)
        self.state.provinces["yukon"].controller = "f0"
        self.unit.location = "great_basin"  # Held by f1.
        refresh_supply(self.state)
        self.assertEqual(recovery_rate(self.state, self.unit), 0)

    def test_fleets_recover_beside_their_own_ports_and_air_groups_at_a_base(self):
        fleet, corps = self.state.units["fleet0"], self.state.units["balloon0"]
        self.assertGreater(recovery_rate(self.state, fleet), 0)
        self.assertGreater(recovery_rate(self.state, corps), 0)
        fleet.location = next(
            sea
            for sea in self.state.naval.adj
            if sea != fleet.location
            and sea not in {s for p, s in self.state.ports.items() if self.state.controls("f0", p)}
        )
        self.assertEqual(recovery_rate(self.state, fleet), 0)
        self.state.provinces[corps.location].controller = "f1"
        self.assertEqual(recovery_rate(self.state, corps), 0)

    def test_units_recover_when_their_turn_begins(self):
        self.unit.hp = 5
        rival = Unit("rival", "f1", "great_basin", hp=5)
        self.state.units[rival.id] = rival
        end_turn(self.state)  # f0 -> f1: only f1 recovers.
        self.assertEqual(self.unit.hp, 5)
        self.assertGreater(rival.hp, 5)


if __name__ == "__main__":
    unittest.main()
