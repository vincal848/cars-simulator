import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from cars.persist import savegame
from cars.persist.savegame import SaveLibrary, load_game, save_game
from cars.sim.balloons import coverage, mission
from cars.sim.campaign import Campaign
from cars.sim.entities import Unit
from cars.sim.market import trade
from cars.sim.objectives import begin, evaluate
from cars.sim.recruitment import recruit
from cars.sim.turn import end_turn
from tests.support import compact, detailed


def embed_map(data: dict) -> None:
    """Rewrite a save the way versions before 4 stored it, with the map copied in."""
    data.update(savegame._expand_map(data))
    del data["map"]


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
        state.provinces[unit.location].buildings.update(farm=2, roads=3, shipyard=1, gasworks=1)
        state.factions["f0"].resources["food"] = 123
        state.round = 9
        restored, geometry, zones, player = self.round_trip(state, shapes, seas)
        self.assertEqual(player, "f0")
        self.assertEqual(restored.round, 9)
        self.assertEqual(asdict(restored.units[unit.id]), asdict(unit))
        self.assertEqual(
            restored.provinces[unit.location].buildings, dict(farm=2, roads=3, shipyard=1, gasworks=1)
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

    def test_objectives_journal_and_ascents(self):
        state, shapes, seas = compact()
        begin(state, "f0")
        evaluate(state, True)
        corps = state.units["balloon0"]
        target = next(p for p in sorted(coverage(state, corps)) if p != corps.location)
        state.units["target"] = Unit("target", "f1", target)
        mission(state, corps.id, target, "observe")
        restored, *_ = self.round_trip(state, shapes, seas)
        self.assertEqual(restored.objectives, state.objectives)
        self.assertEqual(restored.reports, state.reports)
        self.assertEqual(restored.ascents, state.ascents)

    def test_new_units_styles_and_recruitment_limits(self):
        state, shapes, seas = compact()
        state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
        city = state.units["infantry0"].location
        unit_id, _ = recruit(state, city, "scout")
        restored, *_ = self.round_trip(state, shapes, seas)
        self.assertEqual(restored.units[unit_id].kind, "scout")
        self.assertEqual(restored.recruited, [city])
        self.assertEqual(restored.factions["f1"].style, "mexican")
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

    def test_unknown_terrain(self):
        self.assertRejected(lambda data: data["provinces"][0].update(terrain="swamp"))

    def test_unknown_or_overbuilt_buildings(self):
        self.assertRejected(lambda data: data["provinces"][0]["buildings"].update(castle=1))
        self.assertRejected(lambda data: data["provinces"][0]["buildings"].update(roads=4))

    def test_unknown_resources(self):
        self.assertRejected(lambda data: data["provinces"][0]["resource_sites"].update(gold=1))
        self.assertRejected(lambda data: data["factions"][0]["resources"].update(coal=5))
        self.assertRejected(lambda data: data["factions"][0]["resources"].update(food=-1))

    def test_legacy_capacity_metadata_is_accepted(self):
        def add_capacity(data):
            embed_map(data)
            data["version"] = 3
            for edge in data["graphs"]["supply"]["edges"]:
                edge["metadata"]["capacity"] = 10

        self.corrupt(add_capacity)
        state, *_ = load_game(self.path)
        self.assertEqual(state.supply.adj.keys(), self.state.supply.adj.keys())


class UpgradeTests(SaveTestCase):
    def setUp(self):
        super().setUp()
        self.state, self.shapes, self.seas = compact()
        save_game(self.state, self.shapes, self.seas, "f0", self.path)

    def test_older_saves_are_upgraded_step_by_step(self):
        steps = []

        def rename_player(data):
            steps.append(data["version"])
            data["factions"][0]["name"] = "Upgraded Union"
            return data

        library = SaveLibrary(self.path.parent)
        save_game(self.state, self.shapes, self.seas, "f0", library.path(0))
        next_version = savegame.SAVE_VERSION + 1
        upgrades = {savegame.SAVE_VERSION: rename_player}
        with patch.object(savegame, "SAVE_VERSION", next_version), patch.dict(savegame.UPGRADES, upgrades):
            state, *_ = load_game(library.path(0))
            self.assertIn("Upgraded Union", library.describe(0))
        self.assertEqual(steps, [next_version - 1] * 2)  # Once for loading, once for the library listing.
        self.assertEqual(state.factions["f0"].name, "Upgraded Union")

    def test_version_one_saves_start_at_war_with_everyone(self):
        def as_version_one(data):
            embed_map(data)
            data["version"] = 1
            del data["relations"]

        self.corrupt(as_version_one)
        state, *_ = load_game(self.path)
        self.assertEqual(state.relations, {})
        self.assertTrue(state.at_war("f0", "f1"))

    def test_version_two_saves_gain_an_empty_event_log(self):
        def as_version_two(data):
            embed_map(data)
            data["version"] = 2
            del data["events"]

        self.corrupt(as_version_two)
        state, *_ = load_game(self.path)
        self.assertEqual(state.events, {"pending": [], "fired": []})

    def test_unknown_events_are_rejected(self):
        self.corrupt(lambda data: data.update(events={"pending": [], "fired": ["no_such_event"]}))
        with self.assertRaises(ValueError):
            load_game(self.path)

    def test_saves_from_a_newer_game_are_refused_clearly(self):
        self.corrupt(lambda data: data.update(version=savegame.SAVE_VERSION + 1))
        with self.assertRaisesRegex(ValueError, "newer version"):
            load_game(self.path)


class MapReferenceTests(SaveTestCase):
    def test_bundled_maps_are_referenced_not_copied(self):
        state, shapes, seas = detailed()
        begin(state, state.active)
        save_game(state, shapes, seas, state.active, self.path)
        data = json.loads(self.path.read_text())
        self.assertEqual(data["map"]["scenario"], "americas_detailed")
        self.assertNotIn("shapes", data)
        self.assertLess(self.path.stat().st_size, 200_000)
        restored, geometry, zones, _ = load_game(self.path)
        self.assertEqual(geometry, shapes)
        self.assertEqual(zones, seas)
        self.assertEqual(restored.naval.adj, state.naval.adj)

    def test_version_three_saves_drop_their_copy_of_the_map(self):
        state, shapes, seas = compact()
        save_game(state, shapes, seas, "f0", self.path)
        self.corrupt(lambda data: (embed_map(data), data.update(version=3)))
        self.assertEqual(savegame.upgrade(json.loads(self.path.read_text()))["map"]["scenario"], "americas")

    def test_unbundled_maps_are_embedded(self):
        state, shapes, seas = compact()
        shapes = dict(shapes, extra={"type": "Point", "coordinates": [0, 0], "anchor": None})
        _, geometry, *_ = self.round_trip(state, shapes, seas)
        self.assertIn("extra", geometry)
        self.assertIn("shapes", json.loads(self.path.read_text()))

    def test_a_changed_bundled_map_is_refused(self):
        state, shapes, seas = compact()
        save_game(state, shapes, seas, "f0", self.path)
        self.corrupt(lambda data: data["map"].update(digest="0" * 64))
        with self.assertRaisesRegex(ValueError, "different version of the map"):
            load_game(self.path)


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
            self.assertIn("Spring 1836", library.describe(0))
            self.assertTrue(library.has_save())
            with self.assertRaises(ValueError):
                library.path(4)


if __name__ == "__main__":
    unittest.main()
