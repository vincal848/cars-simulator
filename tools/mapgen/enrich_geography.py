"""Give generated provinces real names and add the shaded-relief raster.

Usage: python tools/mapgen/enrich_geography.py path/to/natural-earth-downloads

The folder must contain admin1.geojson, places.geojson, landforms.geojson and the
extracted relief/**/NE1_50M_SR_W.tif. Province borders, graphs and strategic
terrain are left unchanged; only names, city placement and artwork are updated.
"""

import json
import sys
from pathlib import Path

import pygame
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "src" / "cars" / "content"
SCENARIOS = ("americas", "americas_detailed")
ISLAND_CLASSES = ("Island", "Island group")
WESTERN_HEMISPHERE = -30  # Longitude; features east of this are ignored.


def load_features(source: Path, name: str) -> list[dict]:
    return json.loads((source / (name + ".geojson")).read_text(encoding="utf-8"))["features"]


class Gazetteer:
    """Spatial lookups over Natural Earth admin areas, islands and settlements."""

    def __init__(self, source: Path) -> None:
        self.admins = [
            f
            for f in load_features(source, "admin1")
            if f["geometry"] and shape(f["geometry"]).bounds[0] < WESTERN_HEMISPHERE
        ]
        self.admin_shapes = [shape(f["geometry"]).buffer(0) for f in self.admins]
        self.admin_tree = STRtree(self.admin_shapes)
        self.landforms = [f for f in load_features(source, "landforms") if f["geometry"]]
        self.landform_shapes = [shape(f["geometry"]).buffer(0) for f in self.landforms]
        self.landform_tree = STRtree(self.landform_shapes)
        self.places = [
            f
            for f in load_features(source, "places")
            if -180 < f["geometry"]["coordinates"][0] < WESTERN_HEMISPHERE
        ]

    def admin_area(self, point: Point, polygon) -> int:
        """Index of the admin area containing ``point``, else the one overlapping most."""
        candidates = self.admin_tree.query(point, predicate="intersects")
        if not len(candidates):
            candidates = self.admin_tree.query(polygon, predicate="intersects")
        if not len(candidates):
            raise ValueError("No administrative match")
        return max(candidates, key=lambda j: polygon.intersection(self.admin_shapes[j]).area)

    def smallest_island(self, point: Point, admin_area: float) -> str | None:
        """Small real islands give Arctic and archipelago provinces meaningful names."""
        islands = []
        for j in self.landform_tree.query(point, predicate="intersects"):
            info = self.landforms[j]["properties"]
            if info["FEATURECLA"] in ISLAND_CLASSES and self.landform_shapes[j].area < admin_area:
                islands.append((self.landform_shapes[j].area, info.get("NAME_EN") or info["NAME"]))
        return min(islands)[1] if islands else None

    def largest_settlement(self, polygon) -> dict | None:
        inside = [p for p in self.places if polygon.covers(Point(p["geometry"]["coordinates"]))]
        return max(inside, key=lambda p: p["properties"]["POP_MAX"]) if inside else None


def enrich_scenario(name: str, gazetteer: Gazetteer, styles: dict[str, str]) -> None:
    path = CONTENT / "scenarios" / (name + ".json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    world = json.loads((path.parent / raw["geometry"]).read_text(encoding="utf-8"))
    geometry = {f["id"]: f for f in world["features"]}
    for province in raw["provinces"]:
        feature = geometry[province["shape_id"]]
        polygon = shape(feature["geometry"]).buffer(0)
        anchor = feature.get("properties", {}).get("anchor")
        point = Point(anchor) if anchor else polygon.representative_point()
        admin_index = gazetteer.admin_area(point, polygon)
        admin = gazetteer.admins[admin_index]["properties"]
        admin_name = admin.get("name_en") or admin["name"]
        island = gazetteer.smallest_island(point, gazetteer.admin_shapes[admin_index].area)
        province["name"] = island or admin_name
        province["geography"] = dict(
            admin=admin_name,
            country=admin["admin"],
            anchor=[point.x, point.y],
            name_source="physical feature" if island else "administrative area",
            source="Natural Earth 1:10m",
        )
        settlement = gazetteer.largest_settlement(polygon)
        for city in raw["cities"]:
            if city["province"] != province["id"]:
                continue
            if settlement:
                city["name"] = settlement["properties"]["NAME"]
                city["coordinates"] = settlement["geometry"]["coordinates"]
                city["location_source"] = "Natural Earth populated place"
            else:
                city["name"] = province["name"] + " supply hub"
                city["coordinates"] = [point.x, point.y]
                city["location_source"] = "Province supply-hub anchor"
            city["style"] = styles[province["owner"]]
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    distinct = len({p["name"] for p in raw["provinces"]})
    print(f"{name}: {len(raw['provinces'])} provinces, {distinct} distinct names")


def crop_relief(source: Path) -> None:
    """Crop the global raster (30 px/degree) to longitude -180..-30, latitude 80..-60."""
    raster = pygame.image.load(str(next((source / "relief").rglob("*.tif"))))
    width, height = raster.get_size()
    area = (0, int(10 * height / 180), int(150 * width / 360), int(140 * height / 180))
    cropped = raster.subsurface(area).copy()
    target = CONTENT / "map"
    target.mkdir(exist_ok=True)
    pygame.image.save(cropped, str(target / "americas_relief.jpg"))
    print("Relief", cropped.get_size())


def main(source: Path) -> None:
    gazetteer = Gazetteer(source)
    factions = json.loads((CONTENT / "common" / "factions.json").read_text(encoding="utf-8"))
    styles = {f["id"]: f["style"] for f in factions}
    for name in SCENARIOS:
        enrich_scenario(name, gazetteer, styles)
    crop_relief(source)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
