# Map provenance

Made with [Natural Earth](https://www.naturalearthdata.com/). Natural Earth raster and
vector data are [public domain](https://www.naturalearthdata.com/about/terms-of-use/).
The game bundles everything it needs and never downloads map data.

## Coastline and provinces

The detailed scenario uses Natural Earth 1:50m Admin 0 country geometry, retrieved
from the maintainers' repository on September 17, 2026:

- https://github.com/nvkelso/natural-earth-vector
- https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson

Geography is simplified by 0.025 degrees; Greenland and islands smaller than 0.24
square degrees are omitted. The map is clipped to the Americas and drawn in a plain
longitude/latitude projection.

The 186 gameplay provinces are **fictional** Voronoi subdivisions clipped to this
coastline; disconnected pieces become separate provinces. Region names and the
eight faction territories are fictional too. They are not political or
administrative boundary data. River-crossing metadata is an approximate gameplay
example, not a surveyed river dataset, and port links are abstract placements.

Interior borders are meandered after generation, fading to zero at the coast.
Province IDs and graph edges are unaffected, and the output was checked for valid
polygons, negligible overlap and all 224 land edges still joining neighbours.

## Relief, names and cities

- Terrain: Natural Earth I, 1:50m, shaded relief with water:
  https://naciscdn.org/naturalearth/50m/raster/NE1_50M_SR_W.zip
- Administrative names: `ne_10m_admin_1_states_provinces.geojson`
- Island names: `ne_10m_geography_regions_polys.geojson`
- City names and positions: `ne_10m_populated_places.geojson`
- Vector files from the [maintainers' repository](https://github.com/nvkelso/natural-earth-vector/tree/master/geojson),
  downloaded September 18, 2026.

The relief raster is cropped to longitude -180 to -30 and latitude 80 to -60 and
bundled as a 4500 x 4200 JPEG in `src/cars/content/map/`. Source file hashes are
recorded in `src/cars/content/map/geography_sources.json`.

Each province takes the name of the administrative area containing its anchor
point (or overlapping it most), preferring a smaller island name where one applies.
Several fictional provinces can therefore share a real name: the 186 provinces have
109 distinct names. These labels are representative, not claims about real borders.
Every city sits on the largest Natural Earth settlement inside its province.
City artwork is original and stylized, not a reconstruction of real buildings.

## Regenerating

The source downloads stay outside the repository. See
[`tools/mapgen/README.md`](tools/mapgen/README.md) for the commands; they need
Shapely and NumPy, which the game itself does not.
