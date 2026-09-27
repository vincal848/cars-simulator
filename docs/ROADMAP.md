# Roadmap

## Known issues

- **Panning is slow on large windows.** Every drag event re-projects the relief
  raster at full resolution. It should be scaled once per zoom level and shifted
  while panning.

## Next

- Recruitment and construction queues.
- Amphibious transport, maritime supply and port throughput.
- Supply capacity: roads, rails and depots, then max-flow allocation over the
  supply graph.
- Stronger AI: supply awareness, coordinated attacks by several regiments, and
  amphibious invasions (it cannot yet reach nations on other land masses).
- Alliances and military access, so coalition members can cross each other's land.

## Later

- Larger maps: 250 to 400 provinces, 50 to 70 regions and more sea zones, with
  label decluttering.
- Mechanized units, retreats, stacking limits and persistent orders.
- Scenario selection, varied objectives and accessibility options.
- Centrality-based choke-point hints in the strategy inspector.
- Builds for macOS and Linux.
