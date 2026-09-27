"""The map layer: the painted atlas, hit testing and everything drawn over it.

The base map is painted in world space by an Atlas per zoom level and map mode,
so panning only moves cached tiles. Towns, army plates, routes and labels are
drawn in screen space each frame, sized by the UI scale.
"""

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pygame

from cars.sim.entities import BALLOON, FULL_STRENGTH
from cars.sim.regional import CHARTERS
from cars.sim.supply import supplied_provinces, supply_route, threatened_route
from cars.sim.visibility import can_see
from cars.ui.art.buildings import celebration, draw_building
from cars.ui.art.cities import city_sprite
from cars.ui.art.lighting import contact_shadow
from cars.ui.art.regiments import UnitSprites
from cars.ui.camera import Camera, point_in_polygon
from cars.ui.map.animation import MoveAnimation
from cars.ui.map.arrows import draw_route
from cars.ui.map.atlas import OPEN_SEA, Atlas
from cars.ui.map.geometry import Rings, borders, centroid, province_polygons
from cars.ui.map.labels import LABEL_ZOOM, Label, draw_labels, layout_labels
from cars.ui.map.markers import PLATE_SIZE, draw_army, plate_rect
from cars.ui.map.nation_labels import NationNames
from cars.ui.map.relief import RASTER_NORTH, RASTER_WEST

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.kit.ui import Ui

# Map modes.
POLITICAL, TERRAIN, SUPPLY, DIPLOMATIC = "political", "terrain", "supply", "diplomatic"
MAP_MODES = (POLITICAL, TERRAIN, SUPPLY, DIPLOMATIC)

ROUTE = (245, 207, 115)
ATTACK = (232, 104, 80)
SUPPLY_ROUTE = (114, 219, 161)
REACH = (245, 207, 115)
HOVER = (250, 244, 228)
TARGET = (247, 139, 104)
SEA_LABEL = (160, 192, 200)
SEA_LABEL_ALPHA = 200
DEBUG_EDGE = (80, 111, 120)
TOWN_LABEL = (250, 240, 218)
TOWN_LABEL_BACK = (28, 30, 32, 175)
SEA_RING = (149, 171, 181)
# Relation colours for the diplomatic map mode, and supply colours for the supply mode.
OWN, AT_WAR, AT_PEACE = (78, 138, 201), (196, 78, 64), (104, 164, 98)
SUPPLIED, CUT_OFF = (104, 180, 110), (205, 96, 76)
SEA_HIT_RADIUS = 28
ATLAS_CACHE = 4  # Zoom levels and modes whose painted tiles are kept.
DETAIL_ZOOM = 1.8  # Terrain symbols, big towns and building icons.
FIGURES_ZOOM = 1.3  # Unit figures, and towns with their names.


@dataclass
class CityMarker:
    city: str
    point: tuple[float, float]
    rect: pygame.Rect  # the town and its name, for clicking


@dataclass
class Scene:
    """What the map shows this frame."""

    layer: str = "land"
    mode: str = POLITICAL
    unit: "Unit | None" = None
    hover: str | None = None
    inspected: str | None = None
    debug: bool = False
    animation: MoveAnimation | None = None
    mission_mode: str = "observe"
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
    def __init__(self, state: "GameState", shapes: dict, seas: list[dict], ui: "Ui") -> None:
        self.state = state
        self.shapes = shapes
        self.sea_zones = seas
        self.ui = ui
        self.camera = Camera(ui.screen)
        self.sprites = UnitSprites()
        self.mode = POLITICAL
        self.viewer: str | None = None
        self.geometry: dict[str, list[Rings]] = {}
        self.world_anchors: dict[str, tuple[float, float]] = {}
        for province in state.provinces.values():
            shape = shapes[province.shape_id]
            polygons = province_polygons(shape)
            self.geometry[province.id] = polygons
            self.world_anchors[province.id] = shape.get("anchor") or centroid(polygons)
        self.borders = borders(self.geometry)
        self.names = NationNames(state, self.geometry)
        self.seas = {sea["id"]: sea for sea in seas}
        self.world_anchors.update({sea["id"]: sea["anchor"] for sea in seas})
        self._atlases: OrderedDict[tuple, Atlas] = OrderedDict()
        self._fills: dict[str, dict] = {}
        self._pixel = ui.scale
        self._sea_labels: dict[tuple, pygame.Surface] = {}
        self.labels: list[Label] | None = None
        # Army plates drawn this frame: (rect, units in the stack).
        self.plates: list[tuple[pygame.Rect, list[str]]] = []
        # Labels slide with the map while it is dragged and are laid out again once it stops.
        self._panned = self._labels_moved = False
        self.reproject()

    # Projection -----------------------------------------------------------------------

    @property
    def viewport(self) -> pygame.Rect:
        return self.camera.viewport

    def resize(self, viewport: pygame.Rect) -> None:
        """Follow a resized window."""
        self.camera.resize(viewport)
        self.reproject()
        self.labels = None

    def fill(self, mode: str) -> Callable[[str], tuple | None]:
        """Each province's colour in a map mode (None leaves the bare relief)."""
        state = self.state
        viewer = self.viewer or state.active
        if mode == TERRAIN:
            return lambda province: None
        if mode == SUPPLY:
            supplied = supplied_provinces(state, viewer)

            def supply(province: str) -> tuple | None:
                if state.provinces[province].controller != viewer:
                    return None
                return SUPPLIED if province in supplied else CUT_OFF

            return supply
        if mode == DIPLOMATIC:

            def relation(province: str) -> tuple:
                controller = state.provinces[province].controller
                if controller == viewer:
                    return OWN
                return AT_WAR if state.at_war(viewer, controller) else AT_PEACE

            return relation
        return lambda province: tuple(state.factions[state.provinces[province].controller].color)

    @property
    def atlas(self) -> Atlas:
        """The painted map at the current zoom level and map mode."""
        if self._pixel != self.ui.scale:
            self._pixel = self.ui.scale
            self._atlases.clear()
        key = (self.mode, self.camera.scale)
        if key not in self._atlases:
            if self.mode not in self._fills:
                # Remember the colours the new tiles are painted in, to notice when they change.
                fill = self.fill(self.mode)
                self._fills = {self.mode: {p: fill(p) for p in self.state.provinces}}
            zoom = self.camera.zoom_level
            self._atlases[key] = Atlas(
                self.state,
                self.geometry,
                self.borders,
                self.camera.scale,
                names=self.names if self.mode == POLITICAL and zoom < LABEL_ZOOM else None,
                detail=zoom >= DETAIL_ZOOM,
                pixel=self.ui.scale,
                fill=self.fill(self.mode),
            )
            while len(self._atlases) > ATLAS_CACHE:
                self._atlases.popitem(last=False)
        self._atlases.move_to_end(key)
        return self._atlases[key]

    @property
    def origin(self) -> tuple[int, int]:
        """Where the atlas's world pixel (0, 0) falls on screen."""
        return self.camera.project((RASTER_WEST, RASTER_NORTH))

    def reproject(self) -> None:
        """Recompute screen positions of anchors and towns after the camera moves."""
        camera = self.camera
        self._screen_polygons: dict[str, list[Rings]] = {}
        self.anchors = {node: camera.nearest(camera.project(c)) for node, c in self.world_anchors.items()}
        self.city_markers = []
        size = self._town_size()
        for city in self.state.cities.values():
            coordinate = city.coordinates or self.world_anchors[city.province]
            anchor = camera.nearest(camera.project(coordinate))
            for point in camera.copies(anchor):
                if self.viewport.collidepoint(point):
                    rect = pygame.Rect(0, 0, *size)
                    rect.midbottom = (round(point[0]), round(point[1] + size[1] * 0.4))
                    self.city_markers.append(CityMarker(city.id, point, rect))

    def polygons_on_screen(self, province: str) -> list[Rings]:
        """``province``'s outlines in screen coordinates, one set per visible wrapped copy."""
        if province not in self._screen_polygons:
            atlas, (x0, y0) = self.atlas, self.origin
            projected = []
            for shift in range(-2, 3):
                left = x0 + round(shift * self.camera.period)
                if not atlas.bounds[province].move(left, y0).colliderect(self.viewport):
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
        self.camera.home()
        self.reproject()
        self.labels = None

    def center_on(self, node: str, screen_point: tuple[int, int] | None = None) -> None:
        """Pan so that ``node`` appears at ``screen_point`` (the middle of the view by default)."""
        target = screen_point or self.viewport.center
        point = self.camera.nearest(self.camera.project(self.world_anchors[node]))
        self.pan(target[0] - point[0], target[1] - point[1])

    def invalidate_labels(self) -> None:
        self.labels = None

    def _repaint_changed_provinces(self) -> None:
        """Repaint the tiles of provinces whose colour in the current mode has changed."""
        state = self.state
        fill = self.fill(self.mode)
        current = {p: fill(p) for p in state.provinces}
        previous = self._fills.get(self.mode)
        self._fills = {self.mode: current}
        # Other modes are repainted from scratch when next shown.
        for key in [key for key in self._atlases if key[0] != self.mode]:
            del self._atlases[key]
        if previous is None:
            return
        changed = {p for p, color in current.items() if previous.get(p) != color}
        if not changed:
            return
        # The borders of neighbouring provinces change weight too.
        touched = changed | {n for p in changed for n, _ in state.land.neighbors(p)}
        for atlas in self._atlases.values():
            atlas.fill = fill
            atlas.invalidate(touched)

    # Hit testing ----------------------------------------------------------------------

    def city_at(self, point: tuple[int, int]) -> str | None:
        for marker in reversed(self.city_markers):
            if marker.rect.collidepoint(point):
                return marker.city
        return None

    def stack_at(self, point: tuple[int, int]) -> list[str]:
        """The units of the army plate under ``point``, top plate first."""
        for rect, units in reversed(self.plates):
            if rect.collidepoint(point):
                return units
        return []

    def node_at(self, point: tuple[int, int], layer: str) -> str | None:
        """The province (or, on the naval layer, sea zone) under ``point``."""
        city = self.city_at(point)
        if city:
            return self.state.cities[city].province
        if layer == "naval":
            radius = self.ui.px(SEA_HIT_RADIUS)
            for sea in self.seas:
                for x, y in self.camera.copies(self.anchors[sea]):
                    if (point[0] - x) ** 2 + (point[1] - y) ** 2 < radius**2:
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

    def draw(self, screen: pygame.Surface, scene: Scene, reserved: list, covered: list) -> str | None:
        """Draw the map. Returns a line describing the hovered map feature, if any.

        ``reserved`` panels are kept free of labels; labels under ``covered`` panels are hidden.
        """
        if self.camera.viewport != screen.get_rect():
            self.resize(screen.get_rect())
        self.mode, self.viewer = scene.mode, scene.viewer
        screen.fill(OPEN_SEA)
        self._repaint_changed_provinces()
        atlas, origin, period = self.atlas, self.origin, self.camera.period
        atlas.draw(screen, origin, period, self.viewport)
        if scene.visible is not None:
            atlas.draw_fog(screen, origin, period, self.viewport, set(self.state.provinces) - scene.visible)
        atlas.draw_names(screen, origin, period, self.viewport)
        self._draw_province_marks(screen, scene)
        self._draw_sea_zones(screen, scene)
        if scene.debug:
            self._draw_graph(screen, scene.layer)
        description = None
        if scene.mode == SUPPLY and scene.unit and scene.unit.is_land:
            description = self._draw_supply_line(screen, scene.unit)
        self._draw_routes(screen, scene)
        if scene.animation:
            self.route_arrow(screen, scene.animation.route[scene.animation.segment :], ROUTE)
        self._draw_towns(screen, scene.city_hover)
        self._draw_units(screen, scene)
        if scene.layer == "air" and scene.unit:
            description = self._draw_observation(screen, scene) or description
        if self.labels is None or (self._labels_moved and not self._panned):
            self.labels = layout_labels(self, self.ui, reserved)
        self._labels_moved, self._panned = self._panned, False
        draw_labels(screen, self.labels, covered)
        return description

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
        area = self.viewport.inflate(200, 200)
        for offset in (-period, 0, period):
            shifted = [(x + offset, y) for x, y in points]
            if any(area.collidepoint(p) for p in shifted):
                draw_route(screen, shifted, color, self.ui.scale)

    def _draw_province_marks(self, screen, scene: Scene) -> None:
        """Reach, hover and selection outlines, buildings and occupation marks."""
        state = self.state
        ui = self.ui
        detailed = self.camera.zoom_level >= DETAIL_ZOOM
        width = max(2, ui.px(2))
        for province in state.provinces.values():
            outlines = []
            if province.id in scene.highlights:
                outlines.append(SUPPLY_ROUTE if scene.layer == "supply" else REACH)
            if province.id in (scene.inspected, scene.hover):
                outlines.append(HOVER)
            for color in outlines:
                for rings in self.polygons_on_screen(province.id):
                    pygame.draw.lines(screen, color, True, rings[0], width)
            for x, y in self.camera.copies(self.anchors[province.id]):
                # Zoomed out, construction is left to the province panel.
                for i, kind in enumerate(province.buildings if detailed else ()):
                    spot = (x + ui.px(20) + i * ui.px(18), y + ui.px(10))
                    draw_building(screen, kind, spot, ui.px(26), scene.time)
                if province.id in scene.build_effects:
                    celebration(screen, (x, y), scene.time - scene.build_effects[province.id])
                if province.owner != province.controller:
                    # A small dot in the rightful owner's colour marks occupied land.
                    spot = (round(x + ui.px(14)), round(y - ui.px(10)))
                    pygame.draw.circle(screen, (20, 20, 20), spot, ui.px(4))
                    pygame.draw.circle(screen, state.factions[province.owner].color, spot, ui.px(3))

    def _draw_sea_zones(self, screen, scene: Scene) -> None:
        # Waterways come from the relief artwork; province borders are never drawn as rivers.
        naval = scene.layer == "naval"
        for sea, data in self.seas.items():
            lit = sea in scene.highlights
            for x, y in self.camera.copies(self.anchors[sea]):
                label = self._sea_label(data["name"], REACH if lit else SEA_LABEL)
                screen.blit(label, label.get_rect(midtop=(x, y + self.ui.px(22))))
                if naval:
                    rect = pygame.Rect(0, 0, self.ui.px(48), self.ui.px(32))
                    rect.center = (round(x), round(y))
                    pygame.draw.ellipse(screen, REACH if lit else SEA_RING, rect, max(1, self.ui.px(1)))

    def _sea_label(self, name: str, color) -> pygame.Surface:
        """A sea's name in spaced italic capitals, as engraved on period charts."""
        key = (name, color, self.ui.scale, self.ui.font_index)
        if key not in self._sea_labels:
            font = self.ui.font(13, italic=True, serif=True)
            letters = [font.render(letter, True, color) for letter in name.upper()]
            spacing = self.ui.px(3)
            width = sum(letter.get_width() for letter in letters) + spacing * (len(letters) - 1)
            label = pygame.Surface((width, font.get_height()), pygame.SRCALPHA)
            x = 0
            for letter in letters:
                label.blit(letter, (x, 0))
                x += letter.get_width() + spacing
            label.fill((255, 255, 255, SEA_LABEL_ALPHA), special_flags=pygame.BLEND_RGBA_MULT)
            self._sea_labels[key] = label
        return self._sea_labels[key]

    def _draw_graph(self, screen, layer: str) -> None:
        for a, b, _ in self.state.graph(layer).edges():
            if a in self.anchors and b in self.anchors:
                pygame.draw.line(screen, DEBUG_EDGE, self.anchors[a], self.anchors[b], 1)

    def _draw_routes(self, screen, scene: Scene) -> None:
        unit, hover = scene.unit, scene.hover
        if unit and unit.kind == BALLOON and hover in scene.highlights and hover != unit.location:
            self.route_arrow(screen, [unit.location, hover], ROUTE)
        if scene.paths and hover in scene.paths.costs and scene.layer != "supply":
            hostile = (
                hover in self.state.provinces and self.state.provinces[hover].controller != self.state.active
            )
            self.route_arrow(screen, scene.paths.path(hover), ATTACK if hostile else ROUTE)

    def _draw_supply_line(self, screen, unit: "Unit") -> str:
        state = self.state
        route = supply_route(state, unit.owner, unit.location)
        self.route_arrow(screen, route, SUPPLY_ROUTE)
        threats = threatened_route(state, unit.owner, route)
        for province in threats:
            for center in self.camera.copies(self.anchors[province]):
                pygame.draw.circle(screen, ATTACK, center, self.ui.px(13), max(2, self.ui.px(2)))
        if not route:
            return "Cut off: no controlled supply path to a friendly hub."
        hub = next(c.name for c in state.cities.values() if c.province == route[0] and c.supply_hub)
        return f"Supplied from {hub} over {len(route) - 1} links; {len(threats)} threatened."

    def _town_size(self) -> tuple[int, int]:
        zoom = self.camera.zoom_level
        if zoom >= DETAIL_ZOOM:
            return self.ui.px(52), self.ui.px(44)
        if zoom >= FIGURES_ZOOM:
            return self.ui.px(40), self.ui.px(34)
        return self.ui.px(28), self.ui.px(24)

    def _draw_towns(self, screen, hovered: str | None) -> None:
        """Each city as its town and, once zoomed in or hovered, its name."""
        ui = self.ui
        size = self._town_size()
        named = self.camera.zoom_level >= FIGURES_ZOOM
        font = ui.font(13, bold=True)
        placed: list[pygame.Rect] = []
        for marker in self.city_markers:
            city = self.state.cities[marker.city]
            style = city.style or self.state.factions[self.state.provinces[city.province].owner].style
            x, y = marker.point
            contact_shadow(screen, (x + ui.px(7), y + ui.px(6)), (size[0] * 2 // 3, size[1] // 3))
            town = pygame.transform.smoothscale(city_sprite(style), size)
            screen.blit(town, (x - size[0] / 2, y - size[1] * 0.6))
            if not (named or marker.city == hovered):
                continue
            label = font.render(city.name, True, TOWN_LABEL)
            box = label.get_rect(midtop=(round(x), round(y + size[1] * 0.42))).inflate(ui.px(8), ui.px(2))
            if any(box.colliderect(other) for other in placed) and marker.city != hovered:
                continue
            chip = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(chip, TOWN_LABEL_BACK, chip.get_rect(), border_radius=ui.px(3))
            screen.blit(chip, box)
            screen.blit(label, label.get_rect(center=box.center))
            placed.append(box)
            marker.rect = marker.rect.union(box)

    def visible_units(self, scene: Scene) -> list["Unit"]:
        """Units the viewer can see through the fog."""
        return [unit for unit in self.state.units.values() if scene.shows(unit)]

    def _draw_units(self, screen, scene: Scene) -> None:
        """One plate per stack of each arm; a marching unit is drawn on its own along its route."""
        selected = scene.unit.id if scene.unit else None
        marching = scene.animation.unit if scene.animation else None
        stacks: dict[tuple[str, str], list[Unit]] = {}
        for unit in self.visible_units(scene):
            if unit.id != marching:
                arm = "land" if unit.is_land else unit.kind
                stacks.setdefault((unit.location, arm), []).append(unit)
        self.plates = []
        # The selected stack is drawn last, on top of any neighbour it overlaps.
        ordered = sorted(stacks.items(), key=lambda item: any(u.id == selected for u in item[1]))
        figures = self.camera.zoom_level >= FIGURES_ZOOM
        for (location, arm), stack in ordered:
            lead = next((u for u in stack if u.id == selected), stack[0])
            x, y = self.anchors[location]
            # Plates stand beside a town rather than on it...
            x += self._clear_of_towns(x, y + self.ui.px(14) if figures else y)
            if arm == BALLOON:
                # ...and balloon corps beside the armies at their post.
                x += self.ui.px(PLATE_SIZE[0] + 6)
            self._draw_stack(screen, stack, lead, (x, y), lead.id == selected)
        unit = self.state.units.get(marching)
        if unit and scene.shows(unit):
            x, y = scene.animation.position
            self._draw_stack(screen, [unit], unit, (x, y + scene.animation.bob()), unit.id == selected)

    def _draw_stack(self, screen, stack: list["Unit"], lead: "Unit", position, selected: bool) -> None:
        ui = self.ui
        faction = self.state.factions[lead.owner]
        figures = self.camera.zoom_level >= FIGURES_ZOOM
        strength = sum(u.hp for u in stack) / (len(stack) * FULL_STRENGTH)
        for x, y in self.camera.copies(position):
            if not self.viewport.collidepoint((x, y)):
                continue
            plate_y = y + ui.px(14) if figures else y
            if figures:
                # Zoomed in, the leading unit's figure stands on the plate.
                style = CHARTERS[lead.regional].style if lead.regional else faction.style
                sprite = self.sprites.sprite(lead.kind, faction.color, style)
                size = (ui.px(44), ui.px(44)) if lead.is_land else (ui.px(34), ui.px(38))
                contact_shadow(screen, (x + ui.px(2), y + ui.px(8)), (ui.px(38), ui.px(15)))
                figure = pygame.transform.smoothscale(sprite, size)
                screen.blit(figure, (x - size[0] // 2, y + ui.px(8) - size[1]))
            rect = draw_army(
                screen,
                (x, plate_y),
                faction.color,
                lead.kind,
                len(stack),
                strength,
                ui.font(13, bold=True),
                selected=selected,
                supplied=all(u.supplied for u in stack),
                regional=bool(lead.regional),
                scale=ui.scale,
            )
            self.plates.append((rect.inflate(ui.px(4), ui.px(8)), [u.id for u in stack]))

    def _clear_of_towns(self, x: float, y: float) -> float:
        """How far right a plate at (x, y) must step to stand beside a town rather than on it."""
        plate = plate_rect((x, y), self.ui.scale)
        towns = [m.rect for m in self.city_markers if plate.colliderect(m.rect)]
        return max((town.right - plate.left + self.ui.px(4) for town in towns), default=0)

    def _draw_observation(self, screen, scene: Scene) -> str | None:
        """Sights over the provinces the corps' nation has under observation."""
        unit, hover, in_range = scene.unit, scene.hover, scene.highlights
        targets = {ascent["target"] for ascent in self.state.ascents if ascent["owner"] == unit.owner}
        radius, reach, width = self.ui.px(15), self.ui.px(21), max(2, self.ui.px(2))
        for target in targets:
            for cx, cy in self.camera.copies(self.anchors[target]):
                pygame.draw.circle(screen, TARGET, (cx, cy), radius, width)
                for dx, dy in ((-reach, 0), (reach, 0), (0, -reach), (0, reach)):
                    tip = (cx + dx * 0.72, cy + dy * 0.72)
                    pygame.draw.line(screen, TARGET, (cx + dx, cy + dy), tip, width)
        if hover in targets:
            return "Under observation until your next turn."
        if hover not in in_range or hover == unit.location:
            return None
        if scene.mission_mode == "relocate":
            if self.state.controls(unit.owner, hover):
                return "Click to move the corps here."
            return "The corps can only move to a province you control."
        return "Click to go up over this province and spot for your guns."
