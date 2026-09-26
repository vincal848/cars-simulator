"""Compile the detailed Americas scenario from Natural Earth country outlines.

Usage: python tools/mapgen/build_detailed_map.py path/to/ne_50m_admin_0_countries.geojson

Natural Earth geography is public domain. The province divisions are fictional
Voronoi cells clipped to the real coastline.
"""

import json
import random
import sys
from pathlib import Path

import numpy as np
from naturalize_map import naturalize
from shapely import voronoi_polygons
from shapely.geometry import MultiPoint, Point, box, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "src" / "cars" / "content" / "scenarios"
VORONOI_SEEDS = 96  # Islands and coastlines split some cells into several provinces.
MIN_PIECE_AREA = 0.24  # Square degrees; smaller islands are dropped.
SEED = 42
REGION_SEEDS = [
    (-135, 64), (-99, 59), (-122, 46), (-86, 45), (-114, 38), (-79, 37),
    (-110, 29), (-92, 30), (-102, 23), (-89, 20), (-91, 15), (-80, 9),
    (-73, 5), (-59, 6), (-75, -10), (-61, -5), (-69, -19), (-47, -16),
    (-70, -26), (-58, -30), (-70, -41), (-63, -37), (-72, -48), (-67, -54),
]  # fmt: skip


def load_land(source: Path):
    raw = json.loads(Path(source).read_text(encoding="utf-8"))
    countries = [
        shape(f["geometry"])
        for f in raw["features"]
        if f["properties"]["CONTINENT"] in ("North America", "South America")
        and f["properties"]["ADMIN"] != "Greenland"
    ]
    land = unary_union(countries).intersection(box(-170, -57, -30, 76))
    # Close minute gaps between source countries before deriving adjacency.
    return land.buffer(0.0001).buffer(-0.0001).simplify(0.025, preserve_topology=True)


def province_pieces(land) -> list:
    """Farthest-point sampled Voronoi cells, clipped to land and split into polygons."""
    rng = random.Random(SEED)
    candidates = []
    while len(candidates) < 4500:
        point = Point(rng.uniform(-168, -34), rng.uniform(-55, 74))
        if land.contains(point):
            candidates.append(point)
    seeds = [Point(-125, 58)]
    coords = np.array([(p.x, p.y) for p in candidates])
    distances = np.full(len(candidates), np.inf)
    for _ in range(VORONOI_SEEDS - 1):
        distances = np.minimum(distances, ((coords - [seeds[-1].x, seeds[-1].y]) ** 2).sum(axis=1))
        seeds.append(candidates[int(distances.argmax())])
    cells = voronoi_polygons(MultiPoint(seeds), extend_to=box(-180, -65, -20, 85))
    pieces = []
    for cell in cells.geoms:
        clipped = cell.intersection(land)
        parts = [clipped] if clipped.geom_type == "Polygon" else list(clipped.geoms)
        pieces.extend(p for p in parts if p.geom_type == "Polygon" and p.area > MIN_PIECE_AREA)
    pieces.sort(key=lambda p: (-round(p.centroid.y, 3), round(p.centroid.x, 3)))
    return pieces


def strategic_terrain(anchor: Point) -> str:
    in_rockies = -128 < anchor.x < -105 and 28 < anchor.y < 60
    in_andes = -79 < anchor.x < -67 and -48 < anchor.y < 6
    if in_rockies or in_andes:
        return "mountains"
    if anchor.y > 50 or (-15 < anchor.y < 8 and anchor.x > -70):
        return "forest"
    return "plains"


def build(source: Path) -> None:
    land = load_land(source)
    pieces = province_pieces(land)
    anchors = [p.representative_point() for p in pieces]
    compact = json.loads((SCENARIOS / "americas.json").read_text(encoding="utf-8"))
    region_names = [p["name"] for p in compact["provinces"]]

    features, provinces = [], []
    for i, (geometry, anchor) in enumerate(zip(pieces, anchors, strict=True)):
        region = min(range(len(REGION_SEEDS)), key=lambda j: anchor.distance(Point(REGION_SEEDS[j])))
        province_id = f"province_{i:03}"
        terrain = strategic_terrain(anchor)
        provinces.append(
            dict(
                id=province_id,
                name=f"{region_names[region]} {i + 1}",
                region_id=f"r{region}",
                terrain=terrain,
                owner=f"f{region // 3}",
                controller=f"f{region // 3}",
                shape_id=province_id,
                resource_sites={"iron": 1} if terrain == "mountains" else {},
            )
        )
        properties = {"anchor": [anchor.x, anchor.y]}
        features.append(
            dict(type="Feature", id=province_id, properties=properties, geometry=mapping(geometry))
        )

    regions = []
    for i in range(len(REGION_SEEDS)):
        members = [p["id"] for p in provinces if p["region_id"] == f"r{i}"]
        if members:
            production = dict(wood=2, food=3, iron=1)
            regions.append(
                dict(id=f"r{i}", name=region_names[i] + " Region", provinces=members, production=production)
            )

    edges = []
    for i, a in enumerate(pieces):
        for j in range(i + 1, len(pieces)):
            # Only a genuinely shared border connects provinces; never across water.
            if a.boundary.intersection(pieces[j].boundary).length <= 0.005:
                continue
            pa, pb = provinces[i], provinces[j]
            crosses_mississippi = min(anchors[i].x, anchors[j].x) < -91 < max(anchors[i].x, anchors[j].x)
            river = "mississippi" if crosses_mississippi and 29 < anchors[i].y < 47 else None
            both_mountains = pa["terrain"] == "mountains" and pb["terrain"] == "mountains"
            metadata = dict(base_cost=1, river_crossing=river, mountain_pass=both_mountains, infrastructure=1)
            edges.append(dict(a=pa["id"], b=pb["id"], metadata=metadata))

    seas = compact["sea_zones"]
    cities = []
    for region in regions:
        # The best-connected province of each region hosts its city.
        hub = max(region["provinces"], key=lambda p: sum(p in (e["a"], e["b"]) for e in edges))
        index = next(i for i, p in enumerate(provinces) if p["id"] == hub)
        sea = min(seas, key=lambda s: anchors[index].distance(Point(s["anchor"])))["id"]
        name = region["name"].replace("Region", "City")
        cities.append(dict(id="city_" + region["id"], name=name, province=hub, port=sea))

    def owner_of(province_id: str) -> str:
        return next(p for p in provinces if p["id"] == province_id)["owner"]

    units = []
    for faction in range(8):
        held = [c for c in cities if owner_of(c["province"]) == f"f{faction}"]
        for index, city in enumerate(held[:2]):
            unit = dict(
                id=f"infantry{faction}_{index}",
                kind="infantry",
                owner=f"f{faction}",
                location=city["province"],
            )
            units.append(unit)
    capital = next(c for c in cities if owner_of(c["province"]) == "f0")
    units += [
        dict(id="air0", kind="air", owner="f0", location=capital["province"]),
        dict(id="fleet0", kind="fleet", owner="f0", location="north_pacific"),
    ]

    ids = [p["id"] for p in provinces]
    ports = {c["province"]: c["port"] for c in cities}
    naval = compact["graphs"]["naval"]
    air_edges = (
        [dict(a=e["a"], b=e["b"]) for e in edges]
        + [dict(a=p, b=s) for p, s in ports.items()]
        + naval["edges"]
    )
    graphs = dict(
        land=dict(nodes=ids, edges=edges),
        supply=dict(nodes=ids, edges=[dict(a=e["a"], b=e["b"]) for e in edges]),
        naval=naval,
        air=dict(nodes=ids + naval["nodes"], edges=air_edges),
    )
    scenario = dict(
        geometry="americas_detailed.geojson",
        provinces=provinces,
        regions=regions,
        cities=cities,
        units=units,
        ports=ports,
        starting_resources=dict(wood=20, food=18, iron=15),
        sea_zones=seas,
        graphs=graphs,
    )
    (SCENARIOS / "americas_detailed.json").write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    geojson = SCENARIOS / "americas_detailed.geojson"
    geojson.write_text(json.dumps(dict(type="FeatureCollection", features=features)), encoding="utf-8")
    naturalize(geojson)
    print(f"Built {len(provinces)} provinces, {len(regions)} regions, {len(edges)} land borders")


if __name__ == "__main__":
    build(Path(sys.argv[1]))
