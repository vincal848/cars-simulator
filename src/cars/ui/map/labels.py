"""Province name labels that fit wholly inside their (possibly concave) polygon.

Each candidate position is checked with a pixel mask of the province so labels
never spill over borders, coastlines or holes, and never overlap each other,
units or city pins.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from cars.ui.camera import point_in_polygon

if TYPE_CHECKING:
    from cars.ui.kit.ui import Ui
    from cars.ui.map.map_view import MapView

LABEL_INK = (39, 36, 31)
LABEL_ZOOM = 1.45  # Province names appear from this zoom level (nation names below it).
SMALLEST, LARGEST = 12, 17  # Logical font sizes.
# Candidate anchor points, as fractions of the polygon's bounding box, best first.
ANCHOR_FRACTIONS = [(fx, fy) for fy in (0.5, 0.65, 0.35) for fx in (0.5, 0.35, 0.65)]


@dataclass
class Label:
    province: str
    lines: list[str]
    font: pygame.font.Font
    rect: pygame.Rect


def line_variants(name: str) -> list[list[str]]:
    """The name on one line, then every two-line split."""
    words = name.upper().split()
    variants = [[" ".join(words)]]
    variants += [[" ".join(words[:i]), " ".join(words[i:])] for i in range(1, len(words))]
    return variants


def layout_labels(view: "MapView", ui: "Ui", reserved: list[pygame.Rect]) -> list[Label]:
    """Place one label per visible polygon copy where one fits."""
    if view.camera.zoom_level < LABEL_ZOOM:
        return []
    occupied = list(reserved)
    occupied += [
        pygame.Rect(x - ui.px(22), y - ui.px(26), ui.px(44), ui.px(50))
        for unit in view.state.units.values()
        for x, y in view.camera.copies(view.anchors[unit.location])
    ]
    occupied += [marker.rect.inflate(ui.px(12), ui.px(8)) for marker in view.city_markers]
    fonts = {size: ui.font(size) for size in range(SMALLEST, LARGEST + 1)}
    largest = min(LARGEST, max(13, round(view.camera.zoom_level * 3.2)))
    labels = []
    for province in view.state.provinces.values():
        for rings in view.parts[province.id]:
            label = _fit(province.id, province.name, rings, fonts, largest, occupied, view.viewport)
            if label:
                labels.append(label)
                occupied.append(label.rect.inflate(4, 3))
    return labels


def _fit(province_id, name, rings, fonts, largest, occupied, area: pygame.Rect) -> Label | None:
    outer, holes = rings[0], rings[1:]
    xs = [x for x, _ in outer]
    ys = [y for _, y in outer]
    box = pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1).clip(area)
    if box.width < 28 or box.height < 20:
        return None
    surface = pygame.Surface(box.size, pygame.SRCALPHA)
    pygame.draw.polygon(surface, "white", [(x - box.x, y - box.y) for x, y in outer])
    for hole in holes:
        pygame.draw.polygon(surface, (0, 0, 0, 0), [(x - box.x, y - box.y) for x, y in hole])
    mask = pygame.mask.from_surface(surface)

    def on_land(point) -> bool:
        return point_in_polygon(point, outer) and not any(point_in_polygon(point, h) for h in holes)

    variants = line_variants(name)
    for size in range(largest, SMALLEST - 1, -1):
        face = fonts[size]
        for lines in variants:
            width = max(face.size(line)[0] for line in lines) + 4
            height = face.get_linesize() * len(lines) + 2
            if width > box.width or height > box.height:
                continue
            stamp = pygame.mask.Mask((width, height), fill=True)
            for fx, fy in ANCHOR_FRACTIONS:
                rect = pygame.Rect(0, 0, width, height)
                rect.center = (box.x + box.width * fx, box.y + box.height * fy)
                if any(rect.colliderect(other) for other in occupied):
                    continue
                corners = [
                    rect.topleft,
                    (rect.right - 1, rect.top),
                    (rect.left, rect.bottom - 1),
                    (rect.right - 1, rect.bottom - 1),
                ]
                if not all(on_land(corner) for corner in corners):
                    continue
                if mask.overlap_area(stamp, (rect.x - box.x, rect.y - box.y)) != width * height:
                    continue
                return Label(province_id, lines, face, rect)
    return None


def draw_labels(screen: pygame.Surface, labels: list[Label], covered: list[pygame.Rect]) -> None:
    """Draw labels, skipping any hidden under ``covered`` panels."""
    for label in labels:
        if any(panel.colliderect(label.rect) for panel in covered):
            continue
        for i, line in enumerate(label.lines):
            x = label.rect.centerx - label.font.size(line)[0] / 2
            y = label.rect.y + i * label.font.get_linesize()
            screen.blit(label.font.render(line, True, LABEL_INK), (x, y))
