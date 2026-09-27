"""The strategic atlas: an opt-in schematic of the graphs the simulation actually uses.

Normal play stays geographic; this view exposes components, cut points and bridges.
"""

import pygame

from cars.sim.entities import BALLOON, FLEET
from cars.sim.movement import reachable
from cars.sim.naval import reachable_seas
from cars.sim.supply import supplied_provinces
from cars.sim.topology import analyze
from cars.ui.frames import Window
from cars.ui.kit import style

LAYERS = ("land", "supply", "naval", "air")
PICK_RADIUS = 10
EDGE = (150, 140, 120)
NODE = (80, 96, 108)
SUPPLIED = (70, 150, 84)
CUT_OFF = (190, 80, 64)
ROUTE = (50, 110, 170)
BRIDGE = (190, 140, 50)
SIDE = 260


class StrategyWindow(Window):
    name = "strategy"
    title = "Strategic atlas"
    icon = "home"
    size = (1000, 680)

    def __init__(self, game) -> None:
        super().__init__(game)
        self.layer = "land"
        self.selected: str | None = None
        self.points: dict[str, tuple[int, int]] = {}
        self._key: tuple | None = None
        self.metrics = None

    def _owner(self) -> str:
        return self.game.campaign.player or self.state.active

    def _analyze(self):
        state = self.state
        graph = state.graph(self.layer)
        if self.layer == "supply":
            allowed = {p.id for p in state.provinces.values() if p.controller == self._owner()}
        else:
            allowed = set(graph.adj)
        key = (self.layer, tuple(sorted(allowed)))
        if self._key != key:
            self.metrics = analyze(graph, allowed)
            self._key = key
        return graph, self.metrics

    def _layout_points(self, nodes, plot: pygame.Rect) -> None:
        """Fit node anchors into the plot, north up."""
        world = self.game.renderer.map.world_anchors
        anchors = {n: world[n] for n in sorted(nodes) if n in world}
        if not anchors:
            self.points = {}
            return
        xs = [p[0] for p in anchors.values()]
        ys = [p[1] for p in anchors.values()]
        margin = self.ui.px(16)
        scale = min(
            (plot.width - margin * 2) / max(1, max(xs) - min(xs)),
            (plot.height - margin * 2) / max(1, max(ys) - min(ys)),
        )
        self.points = {
            n: (
                int(plot.x + margin + (p[0] - min(xs)) * scale),
                int(plot.y + margin + (max(ys) - p[1]) * scale),
            )
            for n, p in anchors.items()
        }

    def _unit_paths(self):
        """Routes of the selected unit when it moves on this layer."""
        state = self.state
        unit = state.units.get(self.game.view.selected)
        if unit is None:
            return None
        if self.layer == "land" and unit.kind not in (FLEET, BALLOON):
            return reachable(state, unit)
        if self.layer == "naval" and unit.kind == FLEET:
            return reachable_seas(state, unit)
        return None

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        state = self.state
        graph, metrics = self._analyze()
        nodes = metrics.nodes
        supplied = supplied_provinces(state, self._owner())
        button_width = ui.px(120)
        for i, name in enumerate(LAYERS):
            button = pygame.Rect(rect.x + i * (button_width + ui.px(6)), rect.y, button_width, ui.px(30))
            label = "Balloons" if name == "air" else name.title()
            self.button(button, label, "layer:" + name, selected=self.layer == name, icon=name)
        top = rect.y + ui.px(42)
        plot = pygame.Rect(rect.x, top, rect.width - ui.px(SIDE) - ui.px(14), rect.bottom - top)
        ui.inset(plot)
        self.clickable(plot, "plot")
        self._layout_points(nodes, plot)
        line = max(1, ui.px(1))
        for a in self.points:
            for b, _ in graph.neighbors(a):
                if a < b and b in self.points:
                    bridge = tuple(sorted((a, b))) in metrics.bridges
                    pygame.draw.line(
                        ui.surface,
                        BRIDGE if bridge else EDGE,
                        self.points[a],
                        self.points[b],
                        line * (2 if bridge else 1),
                    )
        paths = self._unit_paths()
        if paths and self.selected in paths.costs:
            route = paths.path(self.selected)
            if len(route) > 1:
                pygame.draw.lines(ui.surface, ROUTE, False, [self.points[n] for n in route], line * 3)
        for node, point in self.points.items():
            color = (SUPPLIED if node in supplied else CUT_OFF) if self.layer == "supply" else NODE
            pygame.draw.circle(ui.surface, color, point, ui.px(4))
            if node in metrics.cuts:
                pygame.draw.circle(ui.surface, BRIDGE, point, ui.px(7), line)
            if node == self.selected:
                pygame.draw.circle(ui.surface, style.INK, point, ui.px(10), line * 2)
        side = pygame.Rect(plot.right + ui.px(14), top, ui.px(SIDE), plot.height)
        y = side.y
        for label, value in (
            ("Nodes", len(nodes)),
            ("Components", len(metrics.components)),
            ("Cut points", len(metrics.cuts)),
            ("Bridges", len(metrics.bridges)),
        ):
            ui.text(label, (side.x, y), style.BODY, style.INK_MUTED)
            ui.text(str(value), (side.right, y), style.BODY, style.INK, align="right", bold=True)
            y += ui.px(24)
        y += ui.px(12)
        if self.selected in nodes:
            y += self._details(ui, side, y, graph, metrics, supplied, paths)
        ui.hint(
            plot,
            "Strategic atlas",
            "Click a node to inspect it. Select a unit on the map first to trace its route.",
        )
        self._legend(ui, side)
        return rect.height

    def _legend(self, ui, side: pygame.Rect) -> None:
        """A key to the diagram's marks, along the bottom of the side column."""
        keys = [("ring", BRIDGE, "Cut point"), ("line", BRIDGE, "Bridge"), ("line", ROUTE, "Route")]
        if self.layer == "supply":
            keys += [("dot", SUPPLIED, "Supplied"), ("dot", CUT_OFF, "Cut off")]
        y = side.bottom - len(keys) * ui.px(24)
        for mark, color, label in keys:
            centre = (side.x + ui.px(8), y + ui.px(10))
            if mark == "ring":
                pygame.draw.circle(ui.surface, color, centre, ui.px(7), max(1, ui.px(2)))
            elif mark == "line":
                start, end = (centre[0] - ui.px(8), centre[1]), (centre[0] + ui.px(8), centre[1])
                pygame.draw.line(ui.surface, color, start, end, max(2, ui.px(3)))
            else:
                pygame.draw.circle(ui.surface, color, centre, ui.px(5))
            ui.text(label, (side.x + ui.px(26), y), style.SMALL, style.INK_MUTED)
            y += ui.px(24)

    def _details(self, ui, side: pygame.Rect, y: int, graph, metrics, supplied, paths) -> int:
        node = self.selected
        top = y
        ui.text(
            self.game.renderer.place_name(node),
            (side.x, y),
            style.HEADING,
            style.SLATE,
            bold=True,
            width=side.width,
        )
        y += ui.px(28)
        neighbors = [n for n, _ in graph.neighbors(node) if n in metrics.nodes]
        info = [f"{len(neighbors)} neighbours", f"Component of {len(metrics.component_of(node))}"]
        if self.layer == "supply":
            info.append("Supplied from a hub" if node in supplied else "No connected supply hub")
        if paths:
            info.append(
                f"Move cost {paths.costs[node]:.1f}" if node in paths.costs else "Beyond the unit's reach"
            )
        if node in metrics.cuts:
            info.append("A choke point")
        for line in info:
            ui.text(line, (side.x, y), style.BODY)
            y += ui.px(22)
        return y - top

    def act(self, action: str) -> None:
        verb, _, value = action.partition(":")
        if verb == "layer":
            self.layer = value
            self.selected = None
            self._key = None
        elif verb == "plot":
            mouse = self.ui.mouse()
            candidates = [
                ((mouse[0] - x) ** 2 + (mouse[1] - y) ** 2, node) for node, (x, y) in self.points.items()
            ]
            if candidates:
                distance, node = min(candidates)
                if distance <= self.ui.px(PICK_RADIUS) ** 2:
                    self.selected = node
