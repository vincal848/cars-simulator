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
- **Save validation is incomplete.** Unknown terrain, building or resource keys
  pass validation and only fail later during play.

## Next

- Recruitment and construction queues; reinforcement and healing.
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
