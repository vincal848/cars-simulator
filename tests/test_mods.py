import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tests.support  # noqa: F401  (isolated user profile)
from cars.paths import active_mods, load_content, merge
from cars.sim.events import load_events


class ModTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        self.mods = root / "mods"
        self.env = mock.patch.dict(os.environ, CARS_SAVE_DIR=str(root / "saves"))
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.folder.cleanup()

    def write(self, mod: str, relative: str, data) -> None:
        path = self.mods / mod / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_no_mods_folder_means_bundled_content(self):
        self.assertEqual(active_mods(), [])
        self.assertEqual(load_content("common", "market.json")["lot_size"], 10)

    def test_mods_merge_objects_in_alphabetical_order(self):
        self.write("b_later", "common/market.json", {"lot_size": 5})
        self.write("a_first", "common/market.json", {"lot_size": 7, "sell_ratio": 0.5})
        market = load_content("common", "market.json")
        self.assertEqual(market["lot_size"], 5)
        self.assertEqual(market["sell_ratio"], 0.5)
        self.assertEqual(market["capacity"], 100)
        self.write("a_first", "common/defines.json", {"combat": {"river_attack_factor": 0.5}})
        defines = load_content("common", "defines.json")
        self.assertEqual(defines["combat"]["river_attack_factor"], 0.5)
        self.assertEqual(defines["combat"]["mountain_origin_bonus"], 1.1)

    def test_lists_are_replaced(self):
        self.assertEqual(merge([1, 2], [3]), [3])
        self.write("lessons", "text/tutorial.json", [{"title": "Only", "body": "One.", "goal": "select"}])
        self.assertEqual(len(load_content("text", "tutorial.json")), 1)

    def test_mods_add_and_replace_events(self):
        base = load_events()
        replacement = {
            "id": "bountiful_harvest",
            "title": "Modded Harvest",
            "text": "Changed.",
            "trigger": {"round_at_least": 1},
            "options": [
                {"label": "A", "effects": {"add_gold": 1}},
                {"label": "B", "effects": {"add_gold": 2}},
            ],
        }
        self.write("more_events", "events/extra.json", [replacement, dict(replacement, id="brand_new")])
        events = load_events()
        self.assertEqual(len(events), len(base) + 1)
        self.assertEqual(events["bountiful_harvest"].title, "Modded Harvest")


if __name__ == "__main__":
    unittest.main()
