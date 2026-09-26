# Roadmap

## Known issues

- **Panning is slow on large windows.** Every drag event re-projects the relief
  raster at full resolution. It should be scaled once per zoom level and shifted
  while panning.
- **The AI misjudges attacks.** Its attack estimate ignores terrain, rivers,
  artillery and air support, so it sometimes launches attacks it loses. It should
  use `forecast_order` like the player's forecast card.
- **Saves and replays are about 1.3 MB** because they embed the map geometry.
  They could reference the scenario and a hash instead.
- **Replays are tied to the Python version family.** Python 3.12 changed `sum()`
  over floats, so a replay recorded on 3.12+ may not verify on 3.10 or 3.11 (and
  vice versa). The Windows build always uses 3.13; source installs could require 3.12.
- **The AI ignores the fog of war.** Rivals still see every unit. Enemy zones of
  control also still raise route costs next to hidden armies, which hints at them.
- **Save validation is incomplete.** Unknown terrain, building or resource keys
  pass validation and only fail later during play.

## Next

- Recruitment and construction queues.
- Amphibious transport, maritime supply and port throughput.
- Supply capacity: roads, rails and depots, then max-flow allocation over the
  supply graph.
- Stronger AI: supply awareness, coordinated artillery and invasions.
- Diplomacy between the rival nations.

## Later

- Larger maps: 250 to 400 provinces, 50 to 70 regions and more sea zones, with
  label decluttering.
- Mechanized units, retreats, stacking limits and persistent orders.
- Scenario selection, varied objectives and accessibility options.
- Centrality-based choke-point hints in the strategy inspector.
- Builds for macOS and Linux.
