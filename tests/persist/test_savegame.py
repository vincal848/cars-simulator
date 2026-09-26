import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from cars.persist.savegame import SaveLibrary, load_game, save_game
from cars.sim.air import coverage, mission
from cars.sim.campaign import Campaign
from cars.sim.entities import Unit
from cars.sim.market import trade
from cars.sim.objectives import begin, evaluate
from cars.sim.recruitment import recruit
from cars.sim.turn import end_turn
from tests.support import compact, detailed


class SaveTestCase(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "save.json"

    def tearDown(self):
        self.folder.cleanup()

    def round_trip(self, state, shapes, seas, player="f0"):
        save_game(state, shapes, seas, player, self.path)
        return load_game(self.path)

    def corrupt(self, change) -> None:
        data = json.loads(self.path.read_text())
        change(data)
        self.path.write_text(json.dumps(data))


class RoundTripTests(SaveTestCase):
    def test_changed_campaign_survives(self):
        state, shapes, seas = compact()
        unit = state.units["infantry0"]
        unit.remaining = 2.25
        unit.hp = 7.5
        state.provinces[unit.location].buildings.update(farm=2, roads=3, shipyard=1, airfield=1)
        state.factions["f0"].resources["food"] = 123
        state.round = 9
        restored, geometry, zones, player = self.round_trip(state, shapes, seas)
        self.assertEqual(player, "f0")
        self.assertEqual(restored.round, 9)
        self.assertEqual(asdict(restored.units[unit.id]), asdict(unit))
        self.assertEqual(
            restored.provinces[unit.location].buildings, dict(farm=2, roads=3, shipyard=1, airfield=1)
        )
        self.assertEqual(restored.factions["f0"].resources["food"], 123)
        self.assertEqual(geometry, shapes)
        self.assertEqual(zones, seas)
        self.assertEqual(restored.land.adj, state.land.adj)

    def test_market_treasury_and_calendar(self):
        state, shapes, seas = compact()
        Campaign(state).choose("f0")
        trade(state, "f0", "food", "buy")
        for _ in range(8):
            end_turn(state)
        restored, *_ = self.round_trip(state, shapes, seas)
        self.assertEqual(restored.market, state.market)
        self.assertEqual(restored.factions["f0"].gold, state.factions["f0"].gold)
        self.assertEqual(restored.clock, state.clock)

    def test_objectives_journal_and_air_support(self):
        state, shapes, seas = compact()
        begin(state, "f0")
        evaluate(state, True)
        air = state.units["air0"]
        target = next(p for p in coverage(state, air) if p in state.provinces and p != air.location)
        state.units["target"] = Unit("target", "f1", target)
        mission(state, air.id, target, "support")
        restored, *_ = self.round_trip(state, shapes, seas)
        self.assertEqual(restored.objectives, state.objectives)
        self.assertEqual(restored.reports, state.reports)
        self.assertEqual(restored.air_support, state.air_support)

    def test_new_units_styles_and_recruitment_limits(self):
        state, shapes, seas = compact()
        state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
        city = state.units["infantry0"].location
        unit_id, _ = recruit(state, city, "scout")
        restored, *_ = self.round_trip(state, shapes, seas)
        self.assertEqual(restored.units[unit_id].kind, "scout")
        self.assertEqual(restored.recruited, [city])
        self.assertEqual(restored.factions["f1"].style, "atlantic")
        self.assertIsNone(recruit(restored, city, "artillery")[0])

    def test_city_locations_and_styles(self):
        state, shapes, seas = detailed()
        restored, *_ = self.round_trip(state, shapes, seas)
        for city_id, city in state.cities.items():
            self.assertEqual(city.coordinates, restored.cities[city_id].coordinates)
            self.assertEqual(city.style, restored.cities[city_id].style)


class ValidationTests(SaveTestCase):
    def setUp(self):
        super().setUp()
        self.state, self.shapes, self.seas = compact()
        save_game(self.state, self.shapes, self.seas, "f0", self.path)

    def assertRejected(self, change):
        self.corrupt(change)
        with self.assertRaises(ValueError):
            load_game(self.path)

    def test_unknown_version(self):
        self.path.write_text('{"version": 999}')
        with self.assertRaises(ValueError):
            load_game(self.path)

    def test_saving_outside_the_players_turn(self):
        with self.assertRaises(ValueError):
            save_game(self.state, self.shapes, self.seas, "f1", self.path)

    def test_dangling_unit_location(self):
        self.assertRejected(lambda data: data["units"][0].update(location="missing"))

    def test_invalid_calendar(self):
        self.assertRejected(
            lambda data: data.update(clock={"start_year": 1800, "elapsed": -1, "periods": []})
        )

    def test_missing_fields_are_reported_as_invalid(self):
        self.assertRejected(lambda data: data.pop("market"))

    def test_invalid_tutorial_progress(self):
        self.assertRejected(lambda data: data.update(tutorial={"active": True, "step": 0, "seen": [{}]}))

    def test_legacy_capacity_metadata_is_accepted(self):
        def add_capacity(data):
            for edge in data["graphs"]["supply"]["edges"]:
                edge["metadata"]["capacity"] = 10

        self.corrupt(add_capacity)
        state, *_ = load_game(self.path)
        self.assertEqual(state.supply.adj.keys(), self.state.supply.adj.keys())


class SaveLibraryTests(unittest.TestCase):
    def test_slots_describe_saves_and_unreadable_files(self):
        state, shapes, seas = compact()
        with tempfile.TemporaryDirectory() as folder:
            library = SaveLibrary(Path(folder))
            self.assertEqual(len({library.path(i) for i in range(SaveLibrary.SLOT_COUNT)}), 4)
            self.assertFalse(library.has_save())
            self.assertEqual(library.describe(2), "Empty slot")
            library.path(1).write_text("not json")
            self.assertIn("Unreadable", library.describe(1))
            save_game(state, shapes, seas, "f0", library.path(0))
            self.assertIn("Spring 1800", library.describe(0))
            self.assertTrue(library.has_save())
            with self.assertRaises(ValueError):
                library.path(4)


if __name__ == "__main__":
    unittest.main()
