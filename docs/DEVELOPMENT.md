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

Tests run headless (`tests/support.py` selects SDL's dummy drivers) and keep
saves in a temporary folder, never in your real profile. `ScreenTestCase` gives
you a campaign screen with a faction already chosen, plus helpers to click and
press keys.

Some rules for changes:

- `cars.sim` must not import pygame, and lower layers never import higher ones
  (`tests/test_architecture.py` enforces this).
- Put tuning numbers in `content/common/defines.json`, not in code.
- If a change alters the outcome of any recorded command, bump `RULESET` in
  `persist/replay.py` and regenerate `examples/opening.json`.
- Changing an entity field changes the save format; bump `SAVE_VERSION` in
  `persist/savegame.py` if old saves can no longer load.

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
