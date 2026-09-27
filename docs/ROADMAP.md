# Roadmap

## Art direction

The goal is the look of a grand-strategy atlas in the manner of Europa Universalis,
Victoria and Civilization V, reached in sprints that each land as their own commits:

1. **The map** (done): relief under translucent nation colours, frontier glow,
   two border weights, a dark sea with depths and shallows, cached tiles.
2. **The interface layout:** a full-width top bar for date, treasury and
   stockpiles; a large End Turn button and unit controls bottom right; the
   province window docked to the left edge; objectives as a collapsible tab;
   less ornament, textured panels and stronger text contrast.
3. **Army markers:** one marker per stack with the nation's colour and emblem, a
   regiment count and a strength bar, simplified when zoomed out.
4. **Names on the map:** each nation's name lettered across its territory,
   sea names in a light italic.
5. **Painted artwork:** specifications for event illustrations and leader
   portraits, to be produced with an image generator or taken from public-domain
   sources.

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
