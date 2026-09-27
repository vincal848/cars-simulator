# Changelog

## Unreleased

- **Nations with a history:** each nation has a ruler, capital, government,
  history and two national traits with real effects on recruitment, combat,
  movement, production, upkeep, gold and storage (`common/nations.json`).
- **A new map:** the relief now shows through translucent nation colours, with a
  glow inside each nation's frontier, strong nation borders, faint province
  borders, and a dark sea with visible depths and lighter shallows along the
  coasts. Unclaimed land is left grey.
- **A new interface layout:** a full-width top bar holds your nation, treasury,
  stockpiles and the date; a large round End Turn button sits in the bottom-right
  corner with the map layers, next unit and world view; the province window docks
  on the left; and the objectives panel is narrower and collapses to a tab. The
  title plaque, compass and panel wallpaper are gone, leaving more of the map
  visible.
- **Room for paintings:** event pop-ups, the diplomacy screen and the title screen
  show a painting when one is bundled or supplied by a mod, and fall back to the
  procedural art otherwise. `docs/ART.md` specifies every painting.
- **Names on the map:** zoomed out, each nation's name is lettered along a gentle
  curve across its territory, on two lines where one will not fit, and follows
  its conquests; province names take over when zoomed in. Sea names are set in
  spaced italic capitals.
- **Army markers:** each stack is one plate in its nation's colour with a
  map symbol for its leading arm, a unit count and a strength bar, stepping
  aside from city pins. Zoomed in, the leading unit's figure stands on the plate;
  zoomed out, only plates and city pins are drawn.
- **Smooth panning:** the map is painted once per zoom level in cached tiles;
  panning costs about 3 ms a frame instead of about 145 ms.
- **Recovery:** damaged units regain strength at the start of their turn: +1 when
  supplied in friendly territory (+2 in a city), fleets beside a friendly port and
  air groups at an airbase. The replay ruleset is now 0.25.
- **Upkeep:** units consume food, wood or iron each turn. Shortfalls cost the
  affected units strength and can disband them. The top bar shows net income,
  and rival AIs only recruit what they can feed.
- **Fog of war:** enemy forces are only shown near your territory, units, ports
  and fleets; unseen provinces are shaded. Replays and the F3 view show everything.
- **Diplomacy (D):** offer peace to any rival that is no stronger than you. Peace
  closes both borders and ends attacks for a six-round truce, after which a much
  stronger rival may declare war again. Saves move to format version 2; older
  saves upgrade automatically with every nation at war.
- **Scripted events:** eight events defined as data in `content/events/`, each
  with a trigger and choices. They are offered when your turn begins, must be
  answered, and are saved and replayed. Saves move to format version 3.
- **Smarter, fairer rivals:** the AI judges each attack with the battle rules
  themselves (terrain, rivers, high ground, supply, artillery and air support) and
  only attacks when the province would fall or the exchange favours it. It plays
  under the fog of war, and only enemies in sight exert a zone of control, so route
  costs no longer reveal hidden armies.
- **Tighter economy:** occupied provinces yield half, and each stockpile holds 100
  plus 25 per city; production beyond that spoils. Rivals recruit and build more
  each turn instead of hoarding.
- **Coalitions:** once a nation holds a quarter of the continent's cities, the
  other rivals make peace among themselves and turn on it, and it cannot buy
  peace. In 40-round test games no nation now takes the whole mainland.
- **Mods:** folders in the user-data `mods` directory layer over the bundled
  content: objects merge key by key, lists replace, events are added. See
  `docs/MODDING.md`.
- **Smaller saves:** saves and replays on a bundled map refer to it by name and
  digest instead of copying it, shrinking them from about 1.3 MB to 100 KB. Saves
  move to format version 4; older saves upgrade automatically.
- Python 3.12 or newer is now required. Python 3.12 changed how `sum()` adds
  floats, so replays recorded on older versions could not be verified reliably.
- Saves naming an unknown terrain, building or resource are rejected when opened.
- Golden-master tests, a crash log for the Windows build, and step-by-step
  upgrades for older save formats.
- Restructured the code base: `src/` layout; separate `sim`, `persist` and `ui`
  packages with enforced layering; and small classes for the HUD panels, dialogs,
  map view and rival AI in place of two god objects.
- Tuning constants moved out of code into `content/common/defines.json`, plus new
  `buildings.json`, tutorial and CARSapedia text files.
- Ruff linting and formatting, a lint job in CI, and the test suite reorganised to
  mirror the source tree, with a long-running rival-campaign consistency test.
- The Windows build script now starts from a clean output folder.
- Dropped support for pre-0.17 saves stored inside the project folder.

The restructure itself changed no gameplay, rendering or save files: a 50-round
simulation trace and 39 reference screenshots matched 0.24 exactly.

## 0.24: The music collection

- Three bundled recordings (Bach's Goldberg Aria and Variation 16 performed by
  Kimiko Ishizaka; Grieg's Morning Mood performed by the Musopen Symphony) with
  track selection, shuffle, pause and a separate music volume.

## 0.23: Atlas controls and regional charters

- Collapsible objectives, a season and turn header, and left-drag panning that
  can never issue an order.
- Resizable window and borderless fullscreen (F11 / Alt+Enter).
- 24 regional charters: local regiments with their own uniforms and a 20%
  favoured-terrain movement bonus. The replay ruleset became 0.23.

## 0.22: Learn, inspect and replay

- Ten-lesson guided tutorial, searchable CARSapedia and the strategy inspector.
- Command recording with verified playback; Windows executable and build workflow.

## 0.21: Campaign calendar

- Seasonal dates, visible turn phases and campaign stages from Foothold to Dominion.

## 0.20: Heraldic interface

- Engraved insignia, Estates / Works / Muster tabs and delayed tooltips.

## 0.19: Command polish

- Military overview, next-ready unit navigation and order forecasts.

## 0.18: Campaign systems

- Campaign chronicle, three save slots and an autosave, sound, naval battles, and
  air strike, support and rebase missions with interception.

## 0.15–0.17

- Merchant exchange and gold, then roads, shipyards and airfields with fleet and
  air recruitment. Title screen, MIT license and user-profile saves.

## 0.8–0.14

- Saves and supply-route inspection, then real Natural Earth relief and place
  names, regional uniforms and city architecture, scouts, cavalry and artillery,
  city recruitment, and the city-control objective.

## 0.1–0.7

- First playable graph-driven prototype: the detailed Americas map, movement,
  combat, supply, construction, single-faction campaigns against the AI, and
  the Renaissance-styled interface.
