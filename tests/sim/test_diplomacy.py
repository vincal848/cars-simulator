import unittest

from cars.persist.replay import Playback, Recorder, digest
from cars.sim.ai import faction_actions
from cars.sim.air import mission
from cars.sim.campaign import Campaign
from cars.sim.diplomacy import declare_war, military_strength, propose_peace, truce_ends
from cars.sim.entities import Unit
from cars.sim.movement import hostile_zoc, reachable
from cars.sim.orders import issue_move
from tests.support import compact


class DiplomacyTests(unittest.TestCase):
    def setUp(self):
        self.state, self.shapes, self.seas = compact()
        self.infantry = self.state.units["infantry0"]  # f0 in Yukon, beside f1's Great Basin.

    def test_everyone_starts_at_war(self):
        self.assertTrue(all(self.state.at_war("f0", other) for other in self.state.factions if other != "f0"))
        self.assertFalse(self.state.at_war("f0", "f0"))

    def test_only_a_rival_no_stronger_than_you_accepts_peace(self):
        self.assertGreater(military_strength(self.state, "f0"), military_strength(self.state, "f1"))
        self.assertTrue(propose_peace(self.state, "f0", "f1")[0])
        self.assertFalse(self.state.at_war("f0", "f1"))
        for i in range(5):
            self.state.units[f"guard{i}"] = Unit(f"guard{i}", "f2", "sonora")
        ok, message = propose_peace(self.state, "f0", "f2")
        self.assertFalse(ok)
        self.assertIn("strong enough", message)

    def test_peace_closes_borders_and_calms_zones_of_control(self):
        self.infantry.remaining = 20
        self.assertIn("great_basin", reachable(self.state, self.infantry).costs)
        propose_peace(self.state, "f0", "f1")
        self.assertNotIn("great_basin", reachable(self.state, self.infantry).costs)
        self.assertEqual(issue_move(self.state, self.infantry.id, "great_basin")[0], [])
        self.assertNotIn("canadian_shield", hostile_zoc(self.state, "f0"))

    def test_partners_cannot_strike_each_other(self):
        air = self.state.units["air0"]
        propose_peace(self.state, "f0", "f1")
        self.state.units["partner"] = Unit("partner", "f1", "canadian_shield")
        ok, message = mission(self.state, air.id, "canadian_shield", "strike")
        self.assertFalse(ok)
        self.assertIn("No enemy", message)

    def test_the_truce_must_run_out_before_war(self):
        propose_peace(self.state, "f0", "f1")
        ok, message = declare_war(self.state, "f0", "f1")
        self.assertFalse(ok)
        self.assertIn("truce", message)
        self.state.round = truce_ends(self.state, "f0", "f1")
        self.assertTrue(declare_war(self.state, "f0", "f1")[0])
        self.assertTrue(self.state.at_war("f0", "f1"))

    def test_a_much_stronger_rival_breaks_the_peace_after_the_truce(self):
        propose_peace(self.state, "f0", "f1")
        self.state.round = truce_ends(self.state, "f0", "f1")
        self.state.active_index = 1  # f1's turn.
        for i in range(10):
            self.state.units[f"horde{i}"] = Unit(f"horde{i}", "f1", "great_basin")
        messages = [message for _, _, message in faction_actions(self.state)]
        self.assertIn("declares war", messages[0])
        self.assertTrue(self.state.at_war("f0", "f1"))

    def test_diplomacy_is_recorded_and_replayed(self):
        campaign = Campaign(self.state)
        campaign.choose("f0")
        campaign.recorder = Recorder(self.state, self.shapes, self.seas, "f0")
        self.assertTrue(campaign.propose_peace("f1")[0])
        playback = Playback(campaign.recorder.data())
        self.assertTrue(playback.step())
        self.assertEqual(digest(playback.state), digest(self.state))


if __name__ == "__main__":
    unittest.main()
