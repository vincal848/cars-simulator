# Roadmap

## Known issues

- **Panning is slow on large windows.** Every drag event re-projects the relief
  raster at full resolution. It should be scaled once per zoom level and shifted
  while panning.
- **The economy is too loose.** In 40-round AI games stockpiles grow into the
  thousands and upkeep rarely binds; there is little to spend resources on.
- **One rival usually snowballs.** A single AI tends to take half the continent
  while small nations are wiped out early. Catch-up mechanics or AI coalitions
  against the leader would help.

## Next

- Recruitment and construction queues.
- Amphibious transport, maritime supply and port throughput.
- Supply capacity: roads, rails and depots, then max-flow allocation over the
  supply graph.
- Stronger AI: supply awareness, coordinated artillery and invasions.
- Diplomacy among the rival nations themselves, alliances and military access.

## Later

- Larger maps: 250 to 400 provinces, 50 to 70 regions and more sea zones, with
  label decluttering.
- Mechanized units, retreats, stacking limits and persistent orders.
- Scenario selection, varied objectives and accessibility options.
- Centrality-based choke-point hints in the strategy inspector.
- Builds for macOS and Linux.
