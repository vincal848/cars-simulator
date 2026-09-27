"""Map geometry in longitude and latitude: province outlines and the borders between them.

Neighbouring provinces share their boundary vertices exactly, so every outline
segment belongs either to two provinces (a land border) or to one (a coast or
lake shore). Segments are chained into polylines so borders can be stroked
without gaps at the joints.
"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise

Point = tuple[float, float]
# rings[0] is a polygon's outline and rings[1:] its holes.
Rings = list[list[Point]]


@dataclass(frozen=True)
class Border:
    """A stretch of outline between two provinces, or along one province's coast."""

    provinces: tuple[str, ...]
    line: tuple[Point, ...]

    @property
    def is_coast(self) -> bool:
        return len(self.provinces) == 1


def province_polygons(shape: dict) -> list[Rings]:
    return [shape["coordinates"]] if shape["type"] == "Polygon" else shape["coordinates"]


def borders(geometry: dict[str, list[Rings]]) -> list[Border]:
    """Every border and coastline, as polylines grouped by the provinces they separate."""
    owners: dict[tuple, list[str]] = defaultdict(list)
    ends: dict[tuple, tuple[Point, Point]] = {}
    for province, polygons in geometry.items():
        for rings in polygons:
            for ring in rings:
                for a, b in pairwise(ring):
                    key = _segment_key(a, b)
                    owners[key].append(province)
                    ends[key] = (tuple(a), tuple(b))
    groups: dict[tuple[str, ...], list[tuple[Point, Point]]] = defaultdict(list)
    for key, provinces in owners.items():
        groups[tuple(sorted(set(provinces)))].append(ends[key])
    return [
        Border(provinces, tuple(line))
        for provinces, segments in sorted(groups.items())
        for line in _chain(segments)
    ]


def _point_key(point: Point) -> tuple[float, float]:
    return round(point[0], 6), round(point[1], 6)


def _segment_key(a: Point, b: Point) -> tuple:
    return tuple(sorted((_point_key(a), _point_key(b))))


def _chain(segments: list[tuple[Point, Point]]) -> list[list[Point]]:
    """Join segments that meet end to end into the fewest polylines."""
    touching: dict[tuple, list[int]] = defaultdict(list)
    for index, (a, b) in enumerate(segments):
        touching[_point_key(a)].append(index)
        touching[_point_key(b)].append(index)
    used: set[int] = set()

    def extend(line: list[Point]) -> None:
        while True:
            end = _point_key(line[-1])
            following = next((i for i in touching[end] if i not in used), None)
            if following is None:
                return
            used.add(following)
            a, b = segments[following]
            line.append(b if _point_key(a) == end else a)

    lines = []
    # Start from dead ends first so open borders become single lines.
    starts = sorted(
        range(len(segments)), key=lambda i: min(len(touching[_point_key(p)]) for p in segments[i])
    )
    for index in starts:
        if index in used:
            continue
        used.add(index)
        line = list(segments[index])
        extend(line)
        line.reverse()
        extend(line)
        lines.append(line)
    return lines


def centroid(polygons: list[Rings]) -> Point:
    """Mean vertex of the most detailed outline; a fallback when no label anchor is stored."""
    ring = max(polygons, key=lambda rings: len(rings[0]))[0][:-1]
    return sum(v[0] for v in ring) / len(ring), sum(v[1] for v in ring) / len(ring)
