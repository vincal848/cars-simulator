# Map generation tools

These scripts rebuild the bundled Americas scenario from Natural Earth data. The
game itself never runs them and needs none of their dependencies; the generated
files are committed under `src/cars/content/`.

```sh
python -m pip install -r tools/mapgen/requirements.txt
python tools/mapgen/build_detailed_map.py path/to/ne_50m_admin_0_countries.geojson
python tools/mapgen/enrich_geography.py path/to/natural-earth-downloads
```

1. `build_detailed_map.py` clips the continents to the Americas, splits them into
   Voronoi provinces, derives land borders, cities and starting units, then calls
   `naturalize_map.py` to meander interior borders while keeping coastlines fixed.
   It overwrites only the two `americas_detailed` scenario files.
2. `enrich_geography.py` names provinces after the Natural Earth admin-1 area or
   island that contains them, places cities on real settlements and crops the
   shaded-relief raster. Run it again after any regeneration.

`naturalize_map.py` warps whatever it is given, so never run it twice on the same
output. See `MAP_SOURCES.md` for download links and licensing.
