# Roadmap

## Art direction

The goal is the look of a grand-strategy game in the manner of Victoria,
Europa Universalis and Civilization V. Done so far: the painted political map
with nation names and map modes, army plates and travel arrows; a native-resolution,
scalable interface with a Victoria-style shell of top bar, icon bar, docked
panels and outliner; and a complete CARSapedia. Still to come:

- **Painted artwork:** event illustrations, leader portraits and a title
  backdrop, specified in `docs/ART.md`; the game already shows any painting
  placed where that document says.
- **Map polish:** animated rivers and sea, seasonal tints, and army counters
  that show the strength of each arm in a stack.

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
