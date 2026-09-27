# Development

## Setup

```sh
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"     # Windows: .venv\Scripts\python
```

## Checks

```sh
python -m unittest discover -s tests -t .
ruff check .
ruff format --check .
python -m cars --smoke --faction f0 --screenshot frame.png
```

### Golden tests

`tests/golden` replays 50 rounds of AI campaigns, a recorded player campaign and
every screen at two window sizes (1200×780 at 100% and 1920×1080 at 125%), and
compares hashes of every step with `tests/golden/reference/`. Any
change in behaviour or rendering, however small, fails them. After an intentional
change, regenerate and commit the references in the same commit:

```sh
python -m tests.golden.update
python -m tests.golden.update --dump before/   # at the old commit, then --dump after/ at the new one
```

Diffing the two dump folders shows exactly which step or screen changed. Screen
references depend on pygame, SDL and the installed fonts, so that test skips
itself on machines unlike the one that recorded them (including CI).

Tests run headless (`tests/support.py` selects SDL's dummy drivers) and keep
saves in a temporary folder, never in your real profile. `ScreenTestCase` gives
you a campaign screen with a nation already chosen, plus helpers to click and
press keys; `click_area(frame, action)` clicks wherever a panel or window last
drew a control, so tests never hard-code coordinates.

Some rules for changes:

- `cars.sim` must not import pygame, and lower layers never import higher ones
  (`tests/test_architecture.py` enforces this).
- Put tuning numbers in `content/common/defines.json`, not in code.
- If a change alters the outcome of any recorded command, bump `RULESET` in
  `persist/replay.py` (once per release) and re-record the sample with
  `python tools/rerecord_replay.py examples/opening.json`.
- Changing an entity field changes the save format. Bump `SAVE_VERSION` in
  `persist/savegame.py` and register an upgrade step in `UPGRADES` that converts
  the previous version, so players' existing saves keep loading.

## Releasing the Windows download

1. Update the version in `src/cars/__init__.py` and `packaging/windows/PLAY.txt`,
   and add an entry to `docs/CHANGELOG.md`.
2. Tag the commit `vX.Y.Z` and push the tag. The **Windows download** workflow
   runs the tests, builds with PyInstaller, smoke-tests the executable (title,
   tutorial and example replay) and uploads `CARS-Windows.zip` as an artifact.
3. Download the artifact, extract it and launch `CARS.exe` once by hand.
4. Create a GitHub release for the tag, attach the ZIP and paste the changelog
   entry. The workflow never publishes a release by itself.

To build locally on Windows x64 with Python 3.13:

```powershell
python -m pip install . pygame-ce==2.5.8 pyinstaller==6.22.3
python packaging/windows/build.py
```

The result is `dist/CARS-Windows.zip`. Keep the whole `_internal` folder beside
`CARS.exe`.
