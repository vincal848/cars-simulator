# C.A.R.S. — Combat Arms Region Simulator

**You play on a map. The simulation plays on graphs.**

C.A.R.S. is a turn-based grand-strategy prototype set in an imagined Americas of
1800. Eight nations, each with its own history and national traits, compete over
186 provinces drawn on real Natural Earth geography. You command one; seven AI rivals take their turns. Armies, fleets,
air groups and supply lines each move on their own graph, and every rule works
on those graphs. The map you see is only a way to click on them.

![The campaign map with a route and order forecast](docs/img/campaign.png)

## Features

- **Eight nations with a history**: rulers, capitals, forms of government and two
  national traits each, such as cheaper fleets or stronger mountain defence.
- **A grand-strategy interface** in the manner of Victoria and Europa Universalis:
  a painted political map with nation names, map modes, an outliner, docked
  panels with sortable tables, and an interface that scales from a laptop to a
  4K screen.
- **Land warfare** on a road-, river- and terrain-weighted province graph, with
  zones of control, supply cut-offs, fog of war and deterministic attrition combat.
- **Four unit roles plus navy and air**: infantry, scouts, cavalry and field
  artillery; fleets that fight for sea zones; air groups that strike, support or rebase.
- **Scripted events** defined in data files: harvests, veterans, fevers,
  convoys and more, each with a real choice.
- **Diplomacy**: make peace with rivals that are no stronger than you, and watch
  for the ones that grow strong enough to break it.
- **Economy**: regional wood, food and iron; farms, mills, mines, roads, shipyards
  and airfields; unit upkeep; a merchant exchange for gold.
- **24 regional charters**: named local regiments with their own uniforms and a
  terrain specialty.
- **Order forecasts** that run the real combat rules on a copy of the game, so the
  preview always matches the outcome.
- **Verified replays**: every command is recorded with a hash of the resulting
  state; playback re-simulates the campaign and stops at any divergence.
- **A complete CARSapedia**: nearly a hundred linked articles covering every rule,
  nation, unit, charter, building, terrain and event, with numbers read from the
  game itself so they never go out of date.
- **Guided tutorial and a strategic atlas** that shows the graphs themselves:
  components, choke points and bridges.
- Original procedural artwork, a classical music collection and fully offline play.

<p>
  <img src="docs/img/province.png" width="49%" alt="Province panel with its buildings table">
  <img src="docs/img/diplomacy.png" width="49%" alt="Diplomacy panel and the war screen">
  <img src="docs/img/carsapedia.png" width="49%" alt="CARSapedia article on land battles">
  <img src="docs/img/picker.png" width="49%" alt="Choosing a nation">
</p>

## Play

### Windows download

Download `CARS-Windows.zip` from the [Releases](../../releases) page, extract the
whole folder and run **CARS.exe**. No Python is needed. The build is unsigned, so
Windows may ask for confirmation the first time.

### From source (Windows, macOS, Linux)

Requires Python 3.12 or newer.

```sh
git clone <this repository> && cd CARS
python -m venv .venv
.venv/bin/python -m pip install -e .        # Windows: .venv\Scripts\python ...
.venv/bin/python -m cars
```

On Windows you can also double-click `scripts\run.bat`, which sets up the
environment on first launch; on macOS and Linux run `sh scripts/run.sh`.

Useful options: `--tutorial`, `--faction f0` (skip the picker),
`--fullscreen-windowed`, and `--replay examples/opening.json` to watch a sample.

## How to play

Start with **Guided Tutorial**: ten short lessons that finish when you actually
do each thing. To win a campaign, hold three cities for five consecutive rounds.

![Choosing a nation, marching, the province and diplomacy panels, map modes and the CARSapedia](docs/img/gameplay.gif)

| Input | Action |
| --- | --- |
| Left-click an army plate, then a highlighted province | Move or attack (hover first for the route and forecast) |
| Right-click a province, or click a town | Province panel: facts, production, buildings, recruitment |
| Left-drag / wheel / `Home` | Pan / zoom / world view |
| `1` `2` `3` `4` | Political, terrain, supply and diplomatic map modes |
| `Space` or the round button | End turn; the rivals then act one order at a time |
| `N` / `F` / `Tab` | Next unit with orders / centre selection / next unit in a stack |
| `I` / `U` / `D` / `M` / `J` | Nation / military / diplomacy / market / chronicle panels |
| `F1` / `T` / `G` / `R` | CARSapedia / calendar / strategic atlas / replay studio |
| `F5` / `F9` / `F10` / `F11` | Save / load / settings / fullscreen |
| `Esc` | Close the panel, clear the selection, then open the menu |

The interface size follows your screen (125% at 1080p, 150% at 1440p); change it,
or the typeface, in Settings.

Saves, replays and settings live in your user profile
(`%LOCALAPPDATA%\CARS` on Windows, `~/Library/Application Support/CARS` on macOS,
`~/.local/share/cars` on Linux). Set `CARS_SAVE_DIR` to put them elsewhere.

## Project layout

```
src/cars/
  sim/        game rules: graphs, movement, combat, supply, economy, AI, turns (no pygame)
  persist/    save files and verified replays
  ui/         pygame front end: interface toolkit, map, shell, panels, windows, CARSapedia
  content/    game data, loosely modelled on Paradox's folder layout
    common/     units, buildings, recruitment, market, factions, nations and defines.json
    gfx/        uniform styles
    map/        shaded relief and source hashes
    scenarios/  scenario JSON and province GeoJSON
    text/       CARSapedia entries, unit notes and tutorial lessons
    events/     scripted events with triggers, choices and effects
    music/      bundled recordings
tests/        unit and UI tests, mirroring src/
tools/mapgen/ offline scripts that rebuild the map from Natural Earth
packaging/    Windows executable build
```

Balance lives in data: combat modifiers, movement costs and AI weights are all in
`content/common/defines.json`, so tuning never requires touching code, and mods
can override any of it without editing the game ([docs/MODDING.md](docs/MODDING.md)).
See [docs/DESIGN.md](docs/DESIGN.md) for how the pieces fit together. [docs/ART.md](docs/ART.md)
specifies the optional paintings (event illustrations, leader portraits and the
title backdrop) for anyone who wants to contribute artwork.

## Development

```sh
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -t .   # full suite, headless
python -m cars --smoke                       # render three frames without a window
ruff check . && ruff format --check .
```

CI runs the suite on Windows, macOS and Linux with Python 3.12 and 3.13. Tagging
a `v*` release builds the Windows download; see
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the release checklist and
[docs/ROADMAP.md](docs/ROADMAP.md) for what's next.

## Credits and license

Code and procedural artwork are [MIT licensed](LICENSE). Map data comes from
[Natural Earth](MAP_SOURCES.md) (public domain). Recordings are by Kimiko Ishizaka
(CC0) and the Musopen Symphony (public-domain dedication); see
[MUSIC_CREDITS.md](MUSIC_CREDITS.md). Bundled libraries are listed in
[THIRD_PARTY.md](THIRD_PARTY.md). Provinces, nations and regiments are fictional.
