"""The map layer: the painted atlas, hit testing and everything drawn over it.

The base map is painted in world space by an Atlas per zoom level, so panning
only moves cached tiles. Pins, units, routes and labels are drawn in screen
space each frame.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING

import pygame

from cars.sim.air import STRIKE_TARGET_KINDS, is_airbase
from cars.sim.entities import AIR, FLEET, FULL_STRENGTH
from cars.sim.regional import CHARTERS
from cars.sim.supply import supply_route, threatened_route
from cars.sim.visibility import can_see
from cars.ui.art.buildings import celebration, draw_building
from cars.ui.art.cities import city_sprite, draw_pin
from cars.ui.art.lighting import contact_shadow
from cars.ui.art.regiments import UnitSprites
from cars.ui.camera import Camera, point_in_polygon
from cars.ui.map.animation import MoveAnimation
from cars.ui.map.atlas import OPEN_SEA, Atlas
from cars.ui.map.geometry import Rings, borders, centroid, province_polygons
from cars.ui.map.labels import Label, draw_labels, layout_labels
from cars.ui.map.markers import PLATE_SIZE, draw_army
from cars.ui.map.relief import RASTER_NORTH, RASTER_WEST
from cars.ui.palette import (
    HOSTILE,
    MAP_AREA,
    MAP_MUTED,
    MAP_TEXT,
    ROUTE_GOLD,
    SUPPLY_GREEN,
    TARGET_RED,
)

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.theme import Theme

SEA_LABEL = (109, 143, 151)
DEBUG_EDGE = (80, 111, 120)
CITY_LABEL = (247, 228, 187)
CITY_LABEL_BACK = (43, 35, 32)
CITY_PIN_RADIUS = 11
SEA_HIT_RADIUS = 28
CLOSE_SCALE = 8  # Larger sprites and buildings from this zoom level.
UNIT_CLOSE_SCALE = 6
CITY_NAMES_SCALE = 10
ATLAS_CACHE = 3  # Zoom levels whose painted tiles are kept.


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
        self.geometry: dict[str, list[Rings]] = {}
        self.world_anchors: dict[str, tuple[float, float]] = {}
        for province in state.provinces.values():
            shape = shapes[province.shape_id]
            polygons = province_polygons(shape)
            self.geometry[province.id] = polygons
            self.world_anchors[province.id] = shape.get("anchor") or centroid(polygons)
        self.borders = borders(self.geometry)
        self.seas = {sea["id"]: sea for sea in seas}
        self.world_anchors.update({sea["id"]: sea["anchor"] for sea in seas})
        self._atlases: OrderedDict[float, Atlas] = OrderedDict()
        self._controllers = {p.id: p.controller for p in state.provinces.values()}
        self.labels: list[Label] | None = None
        # Labels slide with the map while it is dragged and are laid out again once it stops.
        self._panned = self._labels_moved = False
        self.reproject()

    # Projection -----------------------------------------------------------------------

    @property
    def atlas(self) -> Atlas:
        """The painted map at the current zoom level."""
        scale = self.camera.scale
        if scale not in self._atlases:
            self._atlases[scale] = Atlas(self.state, self.geometry, self.borders, scale)
            while len(self._atlases) > ATLAS_CACHE:
                self._atlases.popitem(last=False)
        self._atlases.move_to_end(scale)
        return self._atlases[scale]

    @property
    def origin(self) -> tuple[int, int]:
        """Where the atlas's world pixel (0, 0) falls on screen."""
        return self.camera.project((RASTER_WEST, RASTER_NORTH))

    def reproject(self) -> None:
        """Recompute screen positions of anchors and city pins after the camera moves."""
        camera = self.camera
        self._screen_polygons: dict[str, list[Rings]] = {}
        self.anchors = {node: camera.nearest(camera.project(c)) for node, c in self.world_anchors.items()}
        self.city_markers = []
        for city in self.state.cities.values():
            coordinate = city.coordinates or self.world_anchors[city.province]
            anchor = camera.nearest(camera.project(coordinate))
            for point in camera.copies(anchor):
                if MAP_AREA.collidepoint(point):
                    rect = pygame.Rect(point[0] - CITY_PIN_RADIUS, point[1] - CITY_PIN_RADIUS, 22, 22)
                    self.city_markers.append(CityMarker(city.id, point, rect))

    def polygons_on_screen(self, province: str) -> list[Rings]:
        """``province``'s outlines in screen coordinates, one set per visible wrapped copy."""
        if province not in self._screen_polygons:
            atlas, (x0, y0) = self.atlas, self.origin
            projected = []
            for shift in range(-2, 3):
                left = x0 + round(shift * self.camera.period)
                if not atlas.bounds[province].move(left, y0).colliderect(MAP_AREA):
                    continue
                for rings in atlas.polygons[province]:
                    projected.append([[(x + left, y + y0) for x, y in ring] for ring in rings])
            self._screen_polygons[province] = projected
        return self._screen_polygons[province]

    @property
    def parts(self) -> dict[str, list[Rings]]:
        return {province: self.polygons_on_screen(province) for province in self.geometry}

    def pan(self, dx: float, dy: float, dragging: bool = False) -> None:
        """Move the camera. While the map is being ``dragging``, labels slide with it and are
        laid out again once it stops, instead of on every mouse movement."""
        before = self.origin
        self.camera.pan(dx, dy)
        self.reproject()
        if not dragging or not self.labels:
            self.labels = None
            return
        after = self.origin
        period = self.camera.period
        shift_x = after[0] - before[0]
        shift_x -= round(shift_x / period) * period
        for label in self.labels:
            label.rect.move_ip(shift_x, after[1] - before[1])
        self._panned = True

    def zoom(self, factor: float, point: tuple[float, float]) -> None:
        self.camera.zoom(factor, point)
        self.reproject()
        self.labels = None

    def reset_camera(self) -> None:
        self.camera = Camera()
        self.reproject()
        self.labels = None

    def center_on(self, node: str, screen_point: tuple[int, int]) -> None:
        """Pan so that ``node`` appears at ``screen_point``."""
        point = self.camera.nearest(self.camera.project(self.world_anchors[node]))
        self.pan(screen_point[0] - point[0], screen_point[1] - point[1])

    def invalidate_labels(self) -> None:
        self.labels = None

    def _repaint_changed_provinces(self) -> None:
        state = self.state
        changed = {p.id for p in state.provinces.values() if self._controllers[p.id] != p.controller}
        if not changed:
            return
        # The borders of neighbouring provinces change weight too.
        touched = changed | {n for p in changed for n, _ in state.land.neighbors(p)}
        for atlas in self._atlases.values():
            atlas.invalidate(touched)
        self._controllers.update({p: state.provinces[p].controller for p in changed})

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
        atlas, (x0, y0) = self.atlas, self.origin
        world = ((point[0] - x0) % self.camera.period, point[1] - y0)
        for province, polygons in atlas.polygons.items():
            if not atlas.bounds[province].collidepoint(world):
                continue
            for rings in polygons:
                if point_in_polygon(world, rings[0]) and not any(
                    point_in_polygon(world, h) for h in rings[1:]
                ):
                    return province
        return None

    # Drawing --------------------------------------------------------------------------

    def draw(self, screen: pygame.Surface, scene: Scene, message: str, reserved, covered) -> str:
        """Draw the map; returns the status-bar message, which hovered map features may replace.

        ``reserved`` panels are kept free of labels; labels under ``covered`` panels are hidden.
        """
        screen.fill(OPEN_SEA)
        screen.set_clip(MAP_AREA)
        self._repaint_changed_provinces()
        atlas, origin, period = self.atlas, self.origin, self.camera.period
        atlas.draw(screen, origin, period, MAP_AREA)
        if scene.visible is not None:
            atlas.draw_fog(screen, origin, period, MAP_AREA, set(self.state.provinces) - scene.visible)
        self._draw_province_marks(screen, scene)
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
        if self.labels is None or (self._labels_moved and not self._panned):
            self.labels = layout_labels(self, self.theme.font, reserved)
        self._labels_moved, self._panned = self._panned, False
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

    def _draw_province_marks(self, screen, scene: Scene) -> None:
        """Highlights, buildings and occupation marks over the painted provinces."""
        state = self.state
        close = self.camera.scale >= CLOSE_SCALE
        highlight = SUPPLY_GREEN if scene.layer == "supply" else ROUTE_GOLD
        for province in state.provinces.values():
            outlines = []
            if province.id in scene.highlights:
                outlines.append(highlight)
            if province.id in (scene.inspected, scene.hover):
                outlines.append(MAP_TEXT)
            for color in outlines:
                for rings in self.polygons_on_screen(province.id):
                    pygame.draw.lines(screen, color, True, rings[0], 2)
            for x, y in self.camera.copies(self.anchors[province.id]):
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
        """Town sprites, only when zoomed in; zoomed out the pins alone mark the cities."""
        if self.camera.scale < UNIT_CLOSE_SCALE:
            return
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

    def _draw_units(self, screen, scene: Scene) -> None:
        """One marker per stack; a marching unit is drawn on its own along its route."""
        selected = scene.unit.id if scene.unit else None
        marching = scene.animation.unit if scene.animation else None
        stacks: dict[str, list[Unit]] = {}
        for unit in self.visible_units(scene):
            if unit.id != marching:
                stacks.setdefault(unit.location, []).append(unit)
        # The selected stack is drawn last, on top of any neighbour it overlaps.
        for stack in sorted(stacks.values(), key=lambda stack: any(u.id == selected for u in stack)):
            lead = next((u for u in stack if u.id == selected), stack[0])
            self._draw_stack(screen, stack, lead, self.anchors[lead.location], lead.id == selected)
        unit = self.state.units.get(marching)
        if unit and scene.shows(unit):
            x, y = scene.animation.position
            self._draw_stack(screen, [unit], unit, (x, y + scene.animation.bob()), unit.id == selected)

    def _draw_stack(self, screen, stack: list["Unit"], lead: "Unit", position, selected: bool) -> None:
        faction = self.state.factions[lead.owner]
        close = self.camera.scale >= UNIT_CLOSE_SCALE
        strength = sum(u.hp for u in stack) / (len(stack) * FULL_STRENGTH)
        for x, y in self.camera.copies(position):
            if not MAP_AREA.collidepoint((x, y)):
                continue
            plate_y = y + 14 if close else y
            x += self._clear_of_pins(x, plate_y)
            if close:
                # Zoomed in, the leading unit's figure stands on the plate.
                style = CHARTERS[lead.regional].style if lead.regional else faction.style
                sprite = self.sprites.sprite(lead.kind, faction.color, style)
                size = (46, 46) if lead.is_land else (36, 40)
                contact_shadow(screen, (x + 2, y + 8), (40, 16))
                screen.blit(pygame.transform.smoothscale(sprite, size), (x - size[0] // 2, y + 8 - size[1]))
            draw_army(
                screen,
                (x, plate_y),
                faction.color,
                lead.kind,
                len(stack),
                strength,
                self.theme.small,
                selected=selected,
                supplied=all(u.supplied for u in stack),
                regional=bool(lead.regional),
            )

    def _clear_of_pins(self, x: float, y: float) -> float:
        """How far right a marker at (x, y) must step to stand beside a city pin rather than on it."""
        plate = pygame.Rect(0, 0, PLATE_SIZE[0] + 4, PLATE_SIZE[1] + 8)
        plate.center = (x, y)
        pins = [m.rect.inflate(4, 4) for m in self.city_markers if plate.colliderect(m.rect.inflate(4, 4))]
        return max((pin.right - plate.left for pin in pins), default=0)

    def _draw_air_targets(self, screen, scene: Scene) -> str | None:
        unit, hover, in_range = scene.unit, scene.hover, scene.highlights
        targets = {
            other.location
            for other in self.state.units.values()
            if self.state.at_war(unit.owner, other.owner)
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
