import unittest
from unittest.mock import patch

from cars.persist.replay import Playback, Recorder, digest
from cars.sim import events
from cars.sim.campaign import Campaign
from cars.sim.events import EVENTS, check_events, choose_option, parse_event
from cars.sim.turn import end_turn
from tests.support import compact

HARVEST = {
    "id": "test_harvest",
    "title": "Test Harvest",
    "text": "Grain.",
    "trigger": {"round_at_least": 1},
    "options": [
        {"label": "Store it", "effects": {"add_resources": {"food": 25}}},
        {"label": "Sell it", "effects": {"add_gold": 35}},
    ],
}


class EventContentTests(unittest.TestCase):
    def test_bundled_events_are_valid(self):
        self.assertGreaterEqual(len(EVENTS), 8)
        for event in EVENTS.values():
            self.assertGreaterEqual(len(event.options), 2)

    def test_unknown_names_fail_at_load(self):
        for broken in (
            dict(HARVEST, trigger={"moon_is_full": True}),
            dict(HARVEST, options=[{"label": "x", "effects": {"summon_dragon": 1}}] * 2),
            dict(HARVEST, options=[{"label": "x", "effects": {"add_resources": {"gold": 1}}}] * 2),
            dict(HARVEST, options=HARVEST["options"][:1]),
        ):
            with self.assertRaises(ValueError):
                parse_event(broken)


class EventRuleTests(unittest.TestCase):
    def setUp(self):
        self.state, self.shapes, self.seas = compact()
        self.campaign = Campaign(self.state)
        self.campaign.choose("f0")
        self.events = patch.dict(events.EVENTS, {"test_harvest": parse_event(HARVEST)}, clear=True)
        self.events.start()

    def tearDown(self):
        self.events.stop()

    def test_an_event_fires_once_and_waits_for_a_choice(self):
        self.assertEqual(check_events(self.state, "f0"), "test_harvest")
        self.assertIsNone(check_events(self.state, "f0"))
        self.assertEqual(self.state.events, {"pending": ["test_harvest"], "fired": ["test_harvest"]})

    def test_choosing_applies_the_effects(self):
        check_events(self.state, "f0")
        gold = self.state.factions["f0"].gold
        self.assertFalse(choose_option(self.state, "f0", "test_harvest", 5)[0])
        self.assertTrue(choose_option(self.state, "f0", "test_harvest", 1)[0])
        self.assertEqual(self.state.factions["f0"].gold, gold + 35)
        self.assertEqual(self.state.events["pending"], [])
        self.assertEqual(self.state.reports[-1]["kind"], "event")
        self.assertFalse(choose_option(self.state, "f0", "test_harvest", 0)[0])

    def test_events_are_offered_when_the_players_turn_begins(self):
        for _ in range(8):
            end_turn(self.state)
        self.assertEqual(self.state.events["pending"], ["test_harvest"])

    def test_raising_a_unit_places_it_in_a_controlled_city(self):
        before = set(self.state.units)
        events.EFFECTS["raise_unit"](self.state, "f0", "infantry")
        (new,) = set(self.state.units) - before
        unit = self.state.units[new]
        self.assertTrue(self.state.has_city(unit.location))
        self.assertEqual(self.state.provinces[unit.location].controller, "f0")
        self.assertEqual(unit.remaining, 0)

    def test_choices_are_recorded_and_replayed(self):
        check_events(self.state, "f0")
        self.campaign.recorder = Recorder(self.state, self.shapes, self.seas, "f0")
        self.assertTrue(self.campaign.choose_event_option("test_harvest", 0)[0])
        playback = Playback(self.campaign.recorder.data())
        self.assertTrue(playback.step())
        self.assertEqual(digest(playback.state), digest(self.state))


if __name__ == "__main__":
    unittest.main()
