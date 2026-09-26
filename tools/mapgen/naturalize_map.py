"""Meander interior province borders while keeping the coastline exactly in place.

Called by build_detailed_map.py on freshly generated geometry. Never run it twice
on the same file: every run adds another layer of warping.
"""

import json
import math
import sys
from itertools import pairwise
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import unary_union

# Warp amplitude in degrees, and the distance over which it fades out at the coast.
AMPLITUDE = 0.17
DETAIL = 0.08
COAST_FADE = 0.65
SEGMENT_LENGTH = 0.12


def naturalize(path: Path) -> None:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    coast = unary_union([shape(f["geometry"]) for f in data["features"]]).boundary

    def warp(x: float, y: float) -> tuple[float, float]:
        fade = min(1, Point(x, y).distance(coast) / COAST_FADE)
        dx = AMPLITUDE * math.sin(y * 2.1 + x * 0.3) + DETAIL * math.sin(y * 5 + x)
        dy = AMPLITUDE * math.sin(x * 1.9 - y * 0.2) + DETAIL * math.sin(x * 4.7 + y)
        return round(x + fade * dx, 7), round(y + fade * dy, 7)

    def densify(ring: list) -> list:
        result = []
        for a, b in pairwise(ring):
            # Walk each shared edge in a canonical direction so both neighbours
            # insert identical points and their borders stay coincident.
            low, high = sorted([tuple(a), tuple(b)])
            steps = max(1, math.ceil(math.dist(low, high) / SEGMENT_LENGTH))
            points = [
                warp(low[0] + (high[0] - low[0]) * i / steps, low[1] + (high[1] - low[1]) * i / steps)
                for i in range(steps + 1)
            ]
            if tuple(a) != low:
                points.reverse()
            result.extend(points[:-1])
        return [*result, result[0]]

    for feature in data["features"]:
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        warped = [[densify(ring) for ring in polygon] for polygon in polygons]
        geometry["coordinates"] = warped[0] if geometry["type"] == "Polygon" else warped
        polygon = shape(geometry)
        if not polygon.is_valid:
            raise ValueError(f"Warp produced an invalid polygon: {feature['id']}")
        anchor = polygon.representative_point()
        feature["properties"]["anchor"] = [anchor.x, anchor.y]
    path.write_text(json.dumps(data), encoding="utf-8")
    print(f"Naturalized {len(data['features'])} province boundaries")


if __name__ == "__main__":
    naturalize(Path(sys.argv[1]))
