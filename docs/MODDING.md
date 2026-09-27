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

## Nations and traits

`common/nations.json` holds each nation's history, its flag and its two
national traits. A mod can rewrite the history or rebalance a trait by
overriding just the parts it changes.

A flag is a short specification: a `field` colour, equal `stripes` (horizontal
or vertical), the `union` flag, a `rhombus` with a disc, a starred `canton`, and
an `emblem` (`star`, `stars3`, `sun` or `eagle`) at the centre; see
`ui/art/flags.py`. Each trait lists modifiers:

| Modifier | Value | Effect |
| --- | --- | --- |
| `recruit_cost` | `{unit kind: factor}` | Recruitment price |
| `attack` | `{unit kind: factor}` | Attacking strength |
| `defense_terrain` | `{terrain: factor}` | Defending strength in that terrain |
| `defense_home` | factor | Defending strength in the nation's own provinces |
| `movement_terrain` | `{terrain: factor}` | Land movement cost into that terrain |
| `production` | `{resource: factor}` | Income |
| `upkeep` | `{resource: factor}` | Unit upkeep |
| `gold_income` | amount | Extra gold each turn |
| `storage` | amount | Extra stockpile capacity |

Factors multiply and amounts add. Because lists replace rather than merge, a mod
that changes one trait must list both of the nation's traits.

## Paintings

A mod can supply the optional paintings: event illustrations, leader portraits
and the title backdrop. Put them under `gfx/paintings/`, for example
`mods/my_mod/gfx/paintings/events/lean_winter.png`. See
[ART.md](ART.md) for the sizes, names and art direction.

## Things to know

- Replays re-run the rules. A replay recorded with a mod only verifies with the
  same mods active.
- Saves store the units and campaign state they need, but not the rules. Loading a campaign
  with different mods continues it under the new rules.
- Scenarios are separate: start a custom scenario with
  `python -m cars --scenario path/to/scenario.json`.
