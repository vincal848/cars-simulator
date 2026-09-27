import tempfile
import unittest
from pathlib import Path

from cars.persist.replay import Playback, Recorder, apply_command, digest, read_replay_file
from cars.sim.balloons import coverage
from cars.sim.campaign import Campaign
from cars.sim.movement import reachable
from cars.sim.naval import reachable_seas
from cars.sim.supply import refresh_supply
from tests.support import compact, detailed

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "opening.json"


def play_to_end(data: dict) -> Playback:
    playback = Playback(data)
    while playback.step():
        pass
    return playback


class ReplayTests(unittest.TestCase):
    def test_commands_and_rival_turns_reproduce_the_campaign(self):
        for player in ("f0", "f3"):
            state, shapes, seas = detailed()
            campaign = Campaign(state)
            campaign.choose(player)
            campaign.recorder = Recorder(state, shapes, seas, player)
            province = next(p.id for p in state.provinces.values() if p.controller == player)
            campaign.construct(province, "farm")
            campaign.trade("food", "sell")
            for _ in range(3):
                apply_command(state, "end_turn", [])
                campaign.recorder.append(state, "end_turn", [])
            playback = Playback(campaign.recorder.data())
            initial = digest(playback.state)
            while playback.step():
                pass
            self.assertEqual(digest(playback.state), digest(state))
            playback.reset()
            self.assertEqual(digest(playback.state), initial)
            with tempfile.TemporaryDirectory() as folder:
                self.assertTrue(campaign.recorder.export(Path(folder) / "recording.json").exists())

    def test_every_command_type_including_a_failed_attack(self):
        state, shapes, seas = detailed()
        campaign = Campaign(state)
        campaign.choose("f0")
        state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
        infantry = next(u for u in state.units.values() if u.owner == "f0" and u.kind == "infantry")
        target = next(p for p in reachable(state, infantry).costs if p != infantry.location)
        state.provinces[target].controller = "f1"
        # An overwhelming defender guarantees the attack is repelled.
        enemy = next(u for u in state.units.values() if u.owner == "f1" and u.kind == "infantry")
        enemy.location = target
        enemy.defense = enemy.attack = 100
        state.reindex_units()
        refresh_supply(state)
        campaign.recorder = Recorder(state, shapes, seas, "f0")
        campaign.move(infantry.id, target)
        fleet = next(u for u in state.units.values() if u.owner == "f0" and u.kind == "fleet")
        sea = next(p for p in reachable_seas(state, fleet).costs if p != fleet.location)
        self.assertTrue(campaign.move(fleet.id, sea)[0])
        corps = next(u for u in state.units.values() if u.owner == "f0" and u.kind == "balloon")
        self.assertIn(corps.location, coverage(state, corps))
        self.assertTrue(campaign.balloon_mission(corps.id, corps.location, "observe")[0])
        city = next(
            c.province for c in state.cities.values() if state.provinces[c.province].controller == "f0"
        )
        self.assertTrue(campaign.recruit(city, "infantry")[0])
        self.assertEqual(len(campaign.recorder.commands), 4)
        self.assertEqual(digest(play_to_end(campaign.recorder.data()).state), digest(state))

    def test_divergence_and_unknown_commands_stop_playback(self):
        state, shapes, seas = compact()
        Campaign(state).choose("f0")
        recorder = Recorder(state, shapes, seas, "f0")
        apply_command(state, "end_turn", [])
        recorder.append(state, "end_turn", [])

        data = recorder.data()
        data["commands"][0]["after"] = "bad"
        playback = Playback(data)
        before = digest(playback.state)
        with self.assertRaises(ValueError):
            playback.step()
        self.assertEqual(before, digest(playback.state))
        self.assertTrue(playback.failed)
        self.assertFalse(playback.step())

        data = recorder.data()
        data["commands"][0]["action"] = "execute_python"
        playback = Playback(data)
        with self.assertRaises(ValueError):
            playback.step()
        self.assertTrue(playback.failed)

        data["ruleset"] = "other"
        with self.assertRaises(ValueError):
            Playback(data)

    def test_bundled_example_replay_verifies(self):
        playback = play_to_end(read_replay_file(EXAMPLE))
        self.assertEqual(playback.index, len(playback.commands))
        self.assertFalse(playback.failed)


if __name__ == "__main__":
    unittest.main()
