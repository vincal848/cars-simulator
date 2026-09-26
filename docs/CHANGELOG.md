# Changelog

## Unreleased

- Restructured the code base: `src/` layout; separate `sim`, `persist` and `ui`
  packages with enforced layering; and small classes for the HUD panels, dialogs,
  map view and rival AI in place of two god objects.
- Tuning constants moved out of code into `content/common/defines.json`, plus new
  `buildings.json`, tutorial and CARSapedia text files.
- Ruff linting and formatting, a lint job in CI, and the test suite reorganised to
  mirror the source tree, with a long-running rival-campaign consistency test.
- The Windows build script now starts from a clean output folder.
- Dropped support for pre-0.17 saves stored inside the project folder.

Gameplay, rendering, save files and 0.23-ruleset replays are unchanged: a
50-round simulation trace and 39 reference screenshots match the previous
version exactly.

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
