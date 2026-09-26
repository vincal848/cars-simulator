"""Shared test setup: headless SDL, isolated user data and scenario loaders."""

import atexit
import os
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Keep saves, settings and replays out of the real user profile.
_user_data = tempfile.TemporaryDirectory(prefix="cars-tests-")
atexit.register(_user_data.cleanup)
os.environ["CARS_SAVE_DIR"] = os.path.join(_user_data.name, "saves")

from cars.sim.scenario import COMPACT_SCENARIO, DETAILED_SCENARIO, load_scenario  # noqa: E402

SCREEN_SIZE = (1200, 780)


def compact():
    """The small 24-province fixture scenario."""
    return load_scenario(COMPACT_SCENARIO)


def detailed():
    """The full 186-province campaign scenario."""
    return load_scenario(DETAILED_SCENARIO)
