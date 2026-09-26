"""Golden-master tests: the whole game must behave and render exactly as recorded.

If one of these fails after an intentional change, inspect the difference with
``python -m tests.golden.update --dump <folder>`` at both commits, then commit the
regenerated references together with the change.
"""

import unittest

from tests.golden.reference import SCREENS_FILE, SIMULATION_FILE, load, screen_hashes, simulation_hashes


def first_difference(expected: list, actual: list) -> str:
    for (label, want), (got_label, got) in zip(expected, actual, strict=False):
        if label != got_label:
            return f"step order changed at {label!r} (now {got_label!r})"
        if want != got:
            return f"first divergence: {label}"
    return f"{len(expected)} steps recorded, {len(actual)} produced"


class GoldenSimulationTest(unittest.TestCase):
    def test_simulation_matches_reference(self):
        expected = load(SIMULATION_FILE)["steps"]
        actual = simulation_hashes()
        if actual != expected:
            self.fail(first_difference(expected, actual) + ". Regenerate with python -m tests.golden.update.")


class GoldenScreensTest(unittest.TestCase):
    def test_screens_match_reference(self):
        reference = load(SCREENS_FILE)
        environment, actual = screen_hashes()
        if environment != reference["environment"]:
            self.skipTest("Rendering environment (pygame, SDL or fonts) differs from the recording machine")
        if actual != reference["screens"]:
            self.fail(first_difference(reference["screens"], actual) + ". Dump both commits to compare.")


if __name__ == "__main__":
    unittest.main()
