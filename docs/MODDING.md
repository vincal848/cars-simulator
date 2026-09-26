# Modding

Everything that shapes a campaign is data under `src/cars/content/`. A mod is a
folder that mirrors that layout, placed in the `mods` folder beside your saves:

| System | Mods folder |
| --- | --- |
| Windows | `%LOCALAPPDATA%\CARS\mods\` |
| macOS | `~/Library/Application Support/CARS/mods/` |
| Linux | `~/.local/share/cars/mods/` |

Active mods are listed on the title screen. They load in alphabetical order of
their folder names, so later mods win where they overlap.

## How files combine

- **JSON objects are merged key by key.** A mod only needs the values it changes.
  This `mods/gentle_rivers/common/defines.json` lets attackers keep 90% of their
  strength across a river instead of 75%, and leaves every other define alone:

  ```json
  { "combat": { "river_attack_factor": 0.9 } }
  ```

- **Lists replace the bundled list entirely**, for example
  `common/factions.json`, `text/carsapedia.json` or `text/tutorial.json`.
- **Events are added.** Every `events/*.json` file in a mod contributes events,
  and an event with the same `id` as a bundled one replaces it.

## Writing an event

```json
[
  {
    "id": "gold_rush",
    "title": "Gold in the Hills",
    "text": "Prospectors report gold in a remote valley.",
    "trigger": { "round_at_least": 8, "stock_at_least": { "wood": 20 } },
    "options": [
      { "label": "Fund an expedition (-20 wood, +60 gold)", "effects": { "add_resources": { "wood": -20 }, "add_gold": 60 } },
      { "label": "Leave the valley alone", "effects": { "add_gold": 5 } }
    ]
  }
]
```

Every condition in `trigger` must hold when the player's turn begins; each event
fires at most once per campaign. The available names are the `TRIGGERS` and
`EFFECTS` tables in `src/cars/sim/events.py`:

| Triggers | Effects |
| --- | --- |
| `round_at_least`, `cities_at_least`, `cities_below`, `units_at_least`, `damaged_units_at_least`, `gold_at_least`, `stock_below`, `stock_at_least`, `at_peace_with_any` | `add_resources`, `add_gold`, `heal_units`, `weaken_units`, `raise_unit`, `merchant_stock` |

A misspelled name stops the game at start-up with a message naming the event,
instead of failing halfway through a campaign.

## Things to know

- Replays re-run the rules. A replay recorded with a mod only verifies with the
  same mods active.
- Saves store the map and units they need, but not the rules. Loading a campaign
  with different mods continues it under the new rules.
- Scenarios are separate: start a custom scenario with
  `python -m cars --scenario path/to/scenario.json`.
