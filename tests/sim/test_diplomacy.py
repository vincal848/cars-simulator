import unittest

from cars.persist.replay import Playback, Recorder, digest
from cars.sim.ai import faction_actions
from cars.sim.balloons import mission, spotting_at
from cars.sim.campaign import Campaign
from cars.sim.diplomacy import declare_war, leader, military_strength, propose_peace, truce_ends, wants_war
from cars.sim.entities import Unit
from cars.sim.movement import hostile_zoc, reachable
from cars.sim.objectives import begin
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

    def test_peace_stops_the_guns_on_observed_ground(self):
        self.state.provinces["canadian_shield"].controller = "f1"
        mission(self.state, "balloon0", "canadian_shield", "observe")
        self.assertGreater(spotting_at(self.state, "f0", "canadian_shield"), 0)
        propose_peace(self.state, "f0", "f1")
        self.assertEqual(spotting_at(self.state, "f0", "canadian_shield"), 0)

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


class CoalitionTests(unittest.TestCase):
    """f1 takes Sonora's city, giving it a quarter of the continent's cities."""

    def setUp(self):
        self.state, _, _ = compact()
        begin(self.state, "f0")
        self.state.provinces["sonora"].controller = "f1"

    def test_a_quarter_of_the_cities_makes_a_leader(self):
        self.assertEqual(leader(self.state), "f1")
        self.state.provinces["sonora"].controller = "f2"
        self.assertIsNone(leader(self.state))

    def test_rivals_make_peace_with_each_other_but_not_the_player_or_leader(self):
        self.state.active_index = 2
        messages = [message for _, _, message in faction_actions(self.state)]
        self.assertIn("join forces against Atlantic League", messages[0])
        self.assertFalse(self.state.at_war("f2", "f3"))
        self.assertTrue(self.state.at_war("f2", "f1"))
        self.assertTrue(self.state.at_war("f2", "f0"))

    def test_the_leader_is_refused_peace_and_everyone_else_welcomed(self):
        self.state.active_index = 1
        ok, message = propose_peace(self.state, "f1", "f2")
        self.assertFalse(ok)
        self.assertIn("leading power", message)
        self.state.active_index = 0
        for i in range(10):
            self.state.units[f"guard{i}"] = Unit(f"guard{i}", "f2", "gulf_coast")
        self.assertTrue(propose_peace(self.state, "f0", "f2")[0])

    def test_coalition_members_only_go_to_war_with_the_leader(self):
        self.state.active_index = 2
        for other in ("f1", "f3"):
            self.state.relations["|".join(sorted(("f2", other)))] = {"status": "peace", "since": -10}
        for i in range(10):
            self.state.units[f"horde{i}"] = Unit(f"horde{i}", "f2", "gulf_coast")
        self.assertTrue(wants_war(self.state, "f2", "f1"))
        self.assertFalse(wants_war(self.state, "f2", "f3"))
