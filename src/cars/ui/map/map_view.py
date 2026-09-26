"""The map layer: province geometry projected through the camera, hit testing and drawing."""

import math
from collections import Counter
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING

import pygame

from cars.sim.air import STRIKE_TARGET_KINDS, is_airbase
from cars.sim.entities import AIR, FLEET
from cars.sim.regional import CHARTERS
from cars.sim.supply import supply_route, threatened_route
from cars.sim.visibility import can_see
from cars.ui.art.buildings import celebration, draw_building
from cars.ui.art.cities import city_sprite, draw_pin
from cars.ui.art.lighting import contact_shadow
from cars.ui.art.regiments import UnitSprites
from cars.ui.camera import Camera, point_in_polygon
from cars.ui.map.animation import MoveAnimation
from cars.ui.map.labels import Label, draw_labels, layout_labels
from cars.ui.map.relief import illustration_layer, project_relief
from cars.ui.palette import (
    CANVAS_SIZE,
    HOSTILE,
    MAP_AREA,
    MAP_MUTED,
    MAP_TEXT,
    OCEAN,
    ROUTE_GOLD,
    SUPPLY_GREEN,
    TARGET_RED,
)

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

GRATICULE = (30, 53, 64)
SEA_LABEL = (109, 143, 151)
DEBUG_EDGE = (80, 111, 120)
CITY_LABEL = (247, 228, 187)
CITY_LABEL_BACK = (43, 35, 32)
TERRAIN_TINT_ALPHA = 120
BORDER_SHADE = 0.70
CITY_PIN_RADIUS = 11
SEA_HIT_RADIUS = 28
CLOSE_SCALE = 8  # Larger sprites and buildings from this zoom level.
UNIT_CLOSE_SCALE = 6
CITY_NAMES_SCALE = 10
FOG = (8, 14, 20, 105)
COASTLINE = [(8, (26, 43, 46, 95)), (4, (184, 170, 118, 120)), (1, (58, 64, 51, 160))]

# rings[0] is a polygon's outline and rings[1:] its holes, in screen coordinates.
Rings = list[list[tuple[float, float]]]


@dataclass
class CityMarker:
    city: str
    point: tuple[float, float]
    rect: pygame.Rect


@dataclass
class Scene:
    """What the map shows this frame."""

    layer: str
    unit: "Unit | None" = None
    hover: str | None = None
    inspected: str | None = None
    debug: bool = False
    animation: MoveAnimation | None = None
    air_mode: str = "strike"
    paths: "Paths | None" = None
    highlights: set[str] = field(default_factory=set)
    city_hover: str | None = None
    time: float = 0.0
    build_effects: dict[str, float] = field(default_factory=dict)
    viewer: str | None = None
    # Nodes the viewer can see; None disables fog of war.
    visible: set[str] | None = None

    def shows(self, unit: "Unit") -> bool:
        return can_see(unit, self.viewer, self.visible)


class MapView:
    def __init__(self, state: "GameState", shapes: dict, seas: list[dict], theme: "Theme") -> None:
        self.state = state
        self.shapes = shapes
        self.sea_zones = seas
        self.theme = theme
        self.camera = Camera()
        self.sprites = UnitSprites()
        self.sea_font = pygame.font.SysFont("georgia", 15, italic=True)
        self.ocean = _ocean_gradient()
        self.geometry: dict[str, list[Rings]] = {}
        self.world_anchors: dict[str, tuple[float, float]] = {}
        for province in state.provinces.values():
            shape = shapes[province.shape_id]
            polygons = [shape["coordinates"]] if shape["type"] == "Polygon" else shape["coordinates"]
            self.geometry[province.id] = polygons
            self.world_anchors[province.id] = shape.get("anchor") or _centroid(polygons)
        self.coast = _coastline(self.geometry)
        self.seas = {sea["id"]: sea for sea in seas}
        self.world_anchors.update({sea["id"]: sea["anchor"] for sea in seas})
        self._terrain: dict[tuple[str, str], tuple[pygame.Surface, pygame.Rect]] = {}
        self.labels: list[Label] | None = None
        self.reproject()

    # Projection -----------------------------------------------------------------------

    def reproject(self) -> None:
        """Recompute every screen-space cache after the camera moves."""
        camera = self.camera
        self.labels = None
        self.parts: dict[str, list[Rings]] = {}
        for province, polygons in self.geometry.items():
            projected = [[[camera.project(c) for c in ring] for ring in polygon] for polygon in polygons]
            xs = [x for polygon in projected for x, _ in polygon[0]]
            shifts = range(
                math.ceil(-max(xs) / camera.period),
                math.floor((CANVAS_SIZE[0] - min(xs)) / camera.period) + 1,
            )
            copies = [
                [[(x + k * camera.period, y) for x, y in ring] for ring in polygon]
                for k in shifts
                for polygon in projected
            ]
            self.parts[province] = copies or projected
        self.bounds = {province: _bounds(polygons) for province, polygons in self.parts.items()}
        self.anchors = {node: camera.nearest(camera.project(c)) for node, c in self.world_anchors.items()}
        self.city_markers = []
        for city in self.state.cities.values():
            coordinate = city.coordinates or self.world_anchors[city.province]
            anchor = camera.nearest(camera.project(coordinate))
            for point in camera.copies(anchor):
                if MAP_AREA.collidepoint(point):
                    rect = pygame.Rect(point[0] - CITY_PIN_RADIUS, point[1] - CITY_PIN_RADIUS, 22, 22)
                    self.city_markers.append(CityMarker(city.id, point, rect))
        self._terrain.clear()
        self._fog: tuple[frozenset, pygame.Surface] | None = None
        self.relief_surface = project_relief(camera)
        self.illustration_surface = illustration_layer(self.state, self.parts, camera.scale)
        self.coast_surface = self._draw_coast()

    def _draw_coast(self) -> pygame.Surface:
        surface = pygame.Surface(MAP_AREA.size, pygame.SRCALPHA)
        period = self.camera.period
        for width, color in COASTLINE:
            for a, b in self.coast:
                pa, pb = self.camera.project(a), self.camera.project(b)
                for offset in (-period, 0, period):
                    start, end = (pa[0] + offset, pa[1]), (pb[0] + offset, pb[1])
                    if max(start[0], end[0]) >= 0 and min(start[0], end[0]) < CANVAS_SIZE[0]:
                        pygame.draw.line(surface, color, start, end, width)
        return surface

    def pan(self, dx: float, dy: float) -> None:
        self.camera.pan(dx, dy)
        self.reproject()

    def zoom(self, factor: float, point: tuple[float, float]) -> None:
        self.camera.zoom(factor, point)
        self.reproject()

    def reset_camera(self) -> None:
        self.camera = Camera()
        self.reproject()

    def center_on(self, node: str, screen_point: tuple[int, int]) -> None:
        """Pan so that ``node`` appears at ``screen_point``."""
        point = self.camera.nearest(self.camera.project(self.world_anchors[node]))
        self.pan(screen_point[0] - point[0], screen_point[1] - point[1])

    def invalidate_labels(self) -> None:
        self.labels = None

    # Hit testing ----------------------------------------------------------------------

    def city_at(self, point: tuple[int, int]) -> str | None:
        for marker in reversed(self.city_markers):
            dx, dy = point[0] - marker.point[0], point[1] - marker.point[1]
            if dx * dx + dy * dy <= CITY_PIN_RADIUS**2:
                return marker.city
        return None

    def node_at(self, point: tuple[int, int], layer: str) -> str | None:
        """The province (or, on the naval and air layers, sea zone) under ``point``."""
        city = self.city_at(point)
        if city:
            return self.state.cities[city].province
        if layer in ("naval", "air"):
            for sea in self.seas:
                for x, y in self.camera.copies(self.anchors[sea]):
                    if (point[0] - x) ** 2 + (point[1] - y) ** 2 < SEA_HIT_RADIUS**2:
                        return sea
        for province, polygons in self.parts.items():
            if not self.bounds[province].collidepoint(point):
                continue
            for rings in polygons:
                if point_in_polygon(point, rings[0]) and not any(
                    point_in_polygon(point, h) for h in rings[1:]
                ):
                    return province
        return None

    # Drawing --------------------------------------------------------------------------

    def draw(self, screen: pygame.Surface, scene: Scene, message: str, reserved, covered) -> str:
        """Draw the map; returns the status-bar message, which hovered map features may replace.

        ``reserved`` panels are kept free of labels; labels under ``covered`` panels are hidden.
        """
        screen.blit(self.ocean, (0, 0))
        screen.set_clip(MAP_AREA)
        self._draw_graticule(screen)
        screen.blit(self.coast_surface, (0, 0))
        self._draw_provinces(screen, scene)
        if scene.visible is not None:
            screen.blit(self._fog_surface(scene.visible), (0, 0))
        screen.blit(self.illustration_surface, (0, 0))
        self._draw_sea_zones(screen, scene)
        if scene.debug:
            self._draw_graph(screen, scene.layer)
        self._draw_routes(screen, scene)
        if scene.layer == "supply" and scene.unit and scene.unit.is_land:
            message = self._draw_supply_line(screen, scene.unit)
        if scene.animation:
            self._draw_march(screen, scene.animation)
        self._draw_cities(screen)
        self._draw_units(screen, scene)
        if scene.layer == "air" and scene.unit:
            message = self._draw_air_targets(screen, scene) or message
        message = self._draw_city_pins(screen, scene.city_hover) or message
        if self.labels is None:
            self.labels = layout_labels(self, self.theme.font, reserved)
        draw_labels(screen, self.labels, covered)
        screen.set_clip(None)
        return message

    def _plain_text(self, screen, text, position, color, font) -> None:
        screen.blit(font.render(str(text), True, color), position)

    def route_arrow(self, screen: pygame.Surface, path: list[str], color) -> None:
        """Arrow through ``path``, unwrapped so it never jumps across the map seam."""
        if len(path) < 2:
            return
        period = self.camera.period
        points = [self.anchors[path[0]]]
        for node in path[1:]:
            x, y = self.anchors[node]
            x += round((points[-1][0] - x) / period) * period
            points.append((x, y))
        for offset in (-period, 0, period):
            _arrow(screen, [(x + offset, y) for x, y in points], color)

    def _draw_graticule(self, screen) -> None:
        project = self.camera.project
        for longitude in range(-180, -10, 15):
            pygame.draw.line(screen, GRATICULE, project((longitude, 80)), project((longitude, -60)))
        for latitude in range(-60, 90, 15):
            pygame.draw.line(screen, GRATICULE, project((-180, latitude)), project((-20, latitude)))

    def _terrain_surface(self, province) -> tuple[pygame.Surface | None, pygame.Rect]:
        """The relief clipped to ``province`` and tinted in its controller's colour."""
        key = (province.id, province.controller)
        if key not in self._terrain:
            rect = self.bounds[province.id].clip(MAP_AREA)
            if rect.width < 1 or rect.height < 1:
                return None, rect
            surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            surface.blit(self.relief_surface, (-rect.x, -rect.y))
            tint = pygame.Surface(rect.size, pygame.SRCALPHA)
            tint.fill((*self.state.factions[province.controller].color, TERRAIN_TINT_ALPHA))
            surface.blit(tint, (0, 0))
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            for rings in self.parts[province.id]:
                pygame.draw.polygon(
                    mask, (255, 255, 255, 255), [(x - rect.x, y - rect.y) for x, y in rings[0]]
                )
                for hole in rings[1:]:
                    pygame.draw.polygon(mask, (0, 0, 0, 0), [(x - rect.x, y - rect.y) for x, y in hole])
            surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self._terrain[key] = (surface, rect)
        return self._terrain[key]

    def _draw_provinces(self, screen, scene: Scene) -> None:
        state = self.state
        close = self.camera.scale >= CLOSE_SCALE
        highlight = SUPPLY_GREEN if scene.layer == "supply" else ROUTE_GOLD
        for province in state.provinces.values():
            if not self.bounds[province.id].colliderect(MAP_AREA):
                continue
            color = state.factions[province.controller].color
            surface, rect = self._terrain_surface(province)
            if surface:
                screen.blit(surface, rect)
            border = tuple(int(c * BORDER_SHADE) for c in color)
            for rings in self.parts[province.id]:
                outline = rings[0]
                pygame.draw.lines(screen, border, True, outline, 1)
                for hole in rings[1:]:
                    pygame.draw.polygon(screen, OCEAN, hole)
                if province.id in scene.highlights:
                    pygame.draw.lines(screen, highlight, True, outline, 2)
                if province.id in (scene.inspected, scene.hover):
                    pygame.draw.lines(screen, MAP_TEXT, True, outline, 2)
            x, y = self.anchors[province.id]
            if province.buildings:
                for i, kind in enumerate(province.buildings):
                    draw_building(screen, kind, (x + 18 + i * 17, y + 8), 34 if close else 24, scene.time)
                if province.id in scene.build_effects:
                    celebration(screen, (x, y), scene.time - scene.build_effects[province.id])
            if province.owner != province.controller:
                # A small dot in the rightful owner's colour marks occupied land.
                pygame.draw.circle(screen, state.factions[province.owner].color, (x + 12, y - 8), 3)

    def _draw_sea_zones(self, screen, scene: Scene) -> None:
        # Waterways come from the relief artwork; province borders are never drawn as rivers.
        for sea, data in self.seas.items():
            lit = sea in scene.highlights
            for x, y in self.camera.copies(self.anchors[sea]):
                self._plain_text(
                    screen, data["name"], (x - 32, y + 24), ROUTE_GOLD if lit else SEA_LABEL, self.sea_font
                )
                if scene.layer in ("naval", "air"):
                    pygame.draw.ellipse(screen, ROUTE_GOLD if lit else MAP_MUTED, (x - 24, y - 16, 48, 32), 1)

    def _draw_graph(self, screen, layer: str) -> None:
        for a, b, _ in self.state.graph(layer).edges():
            if a in self.anchors and b in self.anchors:
                pygame.draw.line(screen, DEBUG_EDGE, self.anchors[a], self.anchors[b], 1)

    def _draw_routes(self, screen, scene: Scene) -> None:
        unit, hover = scene.unit, scene.hover
        if unit and unit.kind == AIR and hover in scene.highlights and hover != unit.location:
            self.route_arrow(screen, [unit.location, hover], ROUTE_GOLD)
        if scene.paths and hover in scene.paths.costs and scene.layer != "supply":
            hostile = (
                hover in self.state.provinces and self.state.provinces[hover].controller != self.state.active
            )
            self.route_arrow(screen, scene.paths.path(hover), HOSTILE if hostile else ROUTE_GOLD)

    def _draw_supply_line(self, screen, unit: "Unit") -> str:
        state = self.state
        route = supply_route(state, unit.owner, unit.location)
        self.route_arrow(screen, route, SUPPLY_GREEN)
        threats = threatened_route(state, unit.owner, route)
        for province in threats:
            for center in self.camera.copies(self.anchors[province]):
                pygame.draw.circle(screen, HOSTILE, center, 13, 2)
        if not route:
            return (
                "CUT OFF: no controlled supply path to a friendly hub. "
                "Recapture a connecting province or hub."
            )
        hub = next(c.name for c in state.cities.values() if c.province == route[0] and c.supply_hub)
        return (
            f"Supply: {hub} → army / {len(route) - 1} links / {len(threats)} threatened "
            "(adjacent enemy infantry)."
        )

    def _draw_march(self, screen, animation: MoveAnimation) -> None:
        self.route_arrow(screen, animation.route[animation.segment :], ROUTE_GOLD)
        if animation.segment == len(animation.route) - 1:
            for center in self.camera.copies(self.anchors[animation.route[-1]]):
                pygame.draw.circle(screen, ROUTE_GOLD, center, animation.arrival_radius, 1)

    def _draw_cities(self, screen) -> None:
        size = (38, 32) if self.camera.scale < CLOSE_SCALE else (52, 44)
        for marker in self.city_markers:
            city = self.state.cities[marker.city]
            style = city.style or self.state.factions[self.state.provinces[city.province].owner].style
            x, y = marker.point
            contact_shadow(screen, (x + 7, y + 6), (32, 12))
            icon = pygame.transform.smoothscale(city_sprite(style), size)
            screen.blit(icon, (x - size[0] / 2, y - size[1] * 0.58))

    def visible_units(self, scene: Scene) -> list["Unit"]:
        """Units drawn on this layer that the viewer can see through the fog."""
        land_view = scene.layer in ("land", "supply")
        layer_kind = FLEET if scene.layer == "naval" else AIR
        return [
            unit
            for unit in self.state.units.values()
            if (unit.is_land if land_view else unit.kind == layer_kind) and scene.shows(unit)
        ]

    def _fog_surface(self, visible: set[str]) -> pygame.Surface:
        """Shade every province the viewer cannot see, cached until vision changes."""
        key = frozenset(visible)
        if self._fog is None or self._fog[0] != key:
            surface = pygame.Surface(MAP_AREA.size, pygame.SRCALPHA)
            for province, polygons in self.parts.items():
                if province not in key:
                    for rings in polygons:
                        pygame.draw.polygon(surface, FOG, rings[0])
            self._fog = (key, surface)
        return self._fog[1]

    def _draw_units(self, screen, scene: Scene) -> None:
        """One sprite per stack, with the selected unit's stack drawn first."""
        selected = scene.unit.id if scene.unit else None
        units = self.visible_units(scene)
        shown = set()
        for unit in sorted(units, key=lambda u: u.id != selected):
            if unit.location in shown:
                continue
            shown.add(unit.location)
            stack = [other for other in units if other.location == unit.location]
            position = self.anchors[unit.location]
            if scene.animation and scene.animation.unit == unit.id:
                position = (scene.animation.position[0], scene.animation.position[1] + scene.animation.bob())
            for x, y in self.camera.copies(position):
                if MAP_AREA.collidepoint((x, y)):
                    self._draw_unit(screen, unit, (x, y), unit.id == selected, len(stack))

    def _draw_unit(self, screen, unit: "Unit", position, selected: bool, stack_size: int) -> None:
        x, y = position
        faction = self.state.factions[unit.owner]
        contact_shadow(screen, (x + 2, y + 14), (43, 18))
        pygame.draw.ellipse(screen, ROUTE_GOLD if selected else faction.color, (x - 17, y + 10, 34, 10), 2)
        style = CHARTERS[unit.regional].style if unit.regional else faction.style
        sprite = self.sprites.sprite(unit.kind, faction.color, style)
        if unit.regional:
            # A gold diamond marks a regional formation.
            sprite = sprite.copy()
            pygame.draw.polygon(sprite, ROUTE_GOLD, [(4, 0), (8, 5), (4, 10), (0, 5)])
        close = self.camera.scale >= UNIT_CLOSE_SCALE
        if unit.is_land:
            size = (51, 51) if close else (37, 37)
            sprite = pygame.transform.smoothscale(sprite, size)
            screen.blit(sprite, (x - size[0] // 2, y + 17 - size[1]))
        elif not close:
            screen.blit(pygame.transform.smoothscale(sprite, (27, 30)), (x - 13, y - 18))
        else:
            screen.blit(sprite, (x - 18, y - 24))
        pygame.draw.rect(screen, (25, 35, 38), (x - 13, y + 20, 26, 3))
        pygame.draw.rect(screen, (145, 211, 151), (x - 13, y + 20, max(0, int(26 * unit.hp / 10)), 3))
        if stack_size > 1:
            pygame.draw.circle(screen, (39, 28, 30), (int(x + 20), int(y + 13)), 8)
            self._plain_text(screen, str(stack_size), (x + 16, y + 6), ROUTE_GOLD, self.theme.small)
        if not unit.supplied:
            self._plain_text(screen, "!", (x + 16, y - 12), (255, 139, 100), self.theme.body)

    def _draw_air_targets(self, screen, scene: Scene) -> str | None:
        unit, hover, in_range = scene.unit, scene.hover, scene.highlights
        targets = {
            other.location
            for other in self.state.units.values()
            if other.owner != unit.owner
            and other.kind in STRIKE_TARGET_KINDS
            and other.location in in_range
            and scene.shows(other)
        }
        for target in targets:
            for cx, cy in self.camera.copies(self.anchors[target]):
                pygame.draw.circle(screen, TARGET_RED, (cx, cy), 15, 2)
                for dx, dy in ((-21, 0), (21, 0), (0, -21), (0, 21)):
                    pygame.draw.line(
                        screen, TARGET_RED, (cx + dx, cy + dy), (cx + dx * 0.72, cy + dy * 0.72), 2
                    )
        if hover in targets:
            return "Enemy force in range / Strike consumes one sortie / Return fire is possible."
        if hover in in_range and scene.air_mode == "rebase":
            if is_airbase(self.state, unit.owner, hover):
                return "Controlled airbase: click to rebase."
            return "Rebase requires a controlled city airbase or constructed airfield."
        return None

    def _draw_city_pins(self, screen, city_hover: str | None) -> str | None:
        state = self.state
        placed: list[pygame.Rect] = []
        for marker in self.city_markers:
            city = state.cities[marker.city]
            controller = state.provinces[city.province].controller
            draw_pin(screen, marker.point, state.factions[controller].color, marker.city == city_hover)
            if self.camera.scale >= CITY_NAMES_SCALE or marker.city == city_hover:
                label = self.theme.small.render(city.name, True, CITY_LABEL)
                box = label.get_rect(midbottom=(marker.rect.centerx, marker.rect.top - 3)).inflate(8, 4)
                if MAP_AREA.contains(box) and not any(box.colliderect(other) for other in placed):
                    pygame.draw.rect(screen, CITY_LABEL_BACK, box, border_radius=3)
                    screen.blit(label, (box.x + 4, box.y + 2))
                    placed.append(box)
        if not city_hover:
            return None
        city = state.cities[city_hover]
        features = ["1 victory point"]
        if city.supply_hub:
            features.append("Supply hub")
        if city.port:
            features.append("Port connection")
        return city.name + " / " + " / ".join(features) + " / Click pin to inspect"


def _arrow(screen: pygame.Surface, points, color) -> None:
    if len(points) < 2:
        return
    pygame.draw.lines(screen, (12, 24, 32), False, points, 7)
    pygame.draw.lines(screen, color, False, points, 3)
    for a, b in pairwise(points):
        direction = pygame.Vector2(b) - pygame.Vector2(a)
        if direction.length() < 1:
            continue
        direction = direction.normalize()
        head = pygame.Vector2(a).lerp(pygame.Vector2(b), 0.72)
        side = pygame.Vector2(-direction.y, direction.x)
        pygame.draw.polygon(
            screen,
            color,
            [head + direction * 8, head - direction * 5 + side * 5, head - direction * 5 - side * 5],
        )


def _ocean_gradient() -> pygame.Surface:
    surface = pygame.Surface(CANVAS_SIZE)
    height = CANVAS_SIZE[1]
    for y in range(height):
        t = y / height
        color = (int(24 - 8 * t), int(49 - 12 * t), int(60 - 14 * t))
        pygame.draw.line(surface, color, (0, y), (CANVAS_SIZE[0], y))
    return surface


def _centroid(polygons: list[Rings]) -> tuple[float, float]:
    """Mean vertex of the most detailed outline; a fallback when no label anchor is stored."""
    ring = max(polygons, key=lambda rings: len(rings[0]))[0][:-1]
    return sum(v[0] for v in ring) / len(ring), sum(v[1] for v in ring) / len(ring)


def _coastline(geometry: dict[str, list[Rings]]) -> list[tuple]:
    """Polygon edges that belong to exactly one province are coastline."""
    segments: Counter = Counter()
    for polygons in geometry.values():
        for rings in polygons:
            for ring in rings:
                for a, b in pairwise(ring):
                    key = tuple(sorted((tuple(round(v, 6) for v in a), tuple(round(v, 6) for v in b))))
                    segments[key] += 1
    return [segment for segment, count in segments.items() if count == 1]


def _bounds(polygons: list[Rings]) -> pygame.Rect:
    xs = [x for rings in polygons for x, _ in rings[0]]
    ys = [y for rings in polygons for _, y in rings[0]]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
