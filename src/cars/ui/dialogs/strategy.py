"""The strategic atlas: an opt-in schematic of the graphs the simulation actually uses.

Normal play stays geographic; this view exposes components, cut points and bridges.
"""

import pygame

from cars.sim.entities import AIR, FLEET
from cars.sim.movement import reachable
from cars.sim.naval import reachable_seas
from cars.sim.supply import supplied_provinces
from cars.sim.topology import analyze
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import DIM, GOLD

LAYERS = ("land", "supply", "naval", "air")
LAYER_BUTTONS = {name: pygame.Rect(266 + i * 164, 181, 153, 31) for i, name in enumerate(LAYERS)}
PLOT = pygame.Rect(265, 226, 465, 375)
PICK_RADIUS_SQUARED = 100
EDGE = (72, 85, 83)
NODE = (135, 154, 164)
SUPPLIED = (139, 201, 146)
CUT_OFF = (210, 116, 109)
ROUTE = (149, 211, 239)
SELECTED = (255, 241, 200)


class StrategyDialog(Dialog):
    title = "The Strategic Atlas"
    seal = "home"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.layer = "land"
        self.selected: str | None = None
        self.points: dict[str, tuple[int, int]] = {}
        self._key: tuple | None = None
        self.metrics = None

    def handle(self, event: pygame.event.Event) -> None:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self.buttons["close"].collidepoint(event.pos):
            self.game.dialogs.close()
            return
        for name, rect in LAYER_BUTTONS.items():
            if rect.collidepoint(event.pos):
                self.layer = name
                self.selected = None
                self._key = None
                return
        candidates = [
            ((event.pos[0] - x) ** 2 + (event.pos[1] - y) ** 2, node) for node, (x, y) in self.points.items()
        ]
        if candidates:
            distance, node = min(candidates)
            if distance <= PICK_RADIUS_SQUARED:
                self.selected = node

    def _owner(self) -> str:
        return self.game.campaign.player or self.game.state.active

    def _analyze(self):
        state = self.game.state
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

    def _layout_points(self, nodes) -> None:
        """Fit node anchors into the plot, north up."""
        world = self.game.renderer.map.world_anchors
        anchors = {n: world[n] for n in sorted(nodes) if n in world}
        if not anchors:
            self.points = {}
            return
        xs = [p[0] for p in anchors.values()]
        ys = [p[1] for p in anchors.values()]
        scale = min(429 / max(1, max(xs) - min(xs)), 339 / max(1, max(ys) - min(ys)))
        self.points = {
            n: (int(282 + (p[0] - min(xs)) * scale), int(244 + (max(ys) - p[1]) * scale))
            for n, p in anchors.items()
        }

    def _unit_paths(self):
        """Routes of the selected unit when it moves on this layer."""
        state = self.game.state
        unit = state.units.get(self.game.view.selected)
        if unit is None:
            return None
        if self.layer == "land" and unit.kind not in (FLEET, AIR):
            return reachable(state, unit)
        if self.layer == "naval" and unit.kind == FLEET:
            return reachable_seas(state, unit)
        return None

    def draw(self) -> None:
        t = self.theme
        state = self.game.state
        owner = self._owner()
        graph, metrics = self._analyze()
        nodes = metrics.nodes
        supplied = supplied_provinces(state, owner)
        for name, rect in LAYER_BUTTONS.items():
            t.emblem_button(rect, name.title(), name, self.layer == name)
        t.inset(PLOT)
        self._layout_points(nodes)
        for a in self.points:
            for b, _ in graph.neighbors(a):
                if a < b and b in self.points:
                    bridge = tuple(sorted((a, b))) in metrics.bridges
                    pygame.draw.line(
                        t.screen, GOLD if bridge else EDGE, self.points[a], self.points[b], 2 if bridge else 1
                    )
        paths = self._unit_paths()
        if paths and self.selected in paths.costs:
            route = paths.path(self.selected)
            if len(route) > 1:
                pygame.draw.lines(t.screen, ROUTE, False, [self.points[n] for n in route], 3)
        for node, point in self.points.items():
            if self.layer == "supply":
                color = SUPPLIED if node in supplied else CUT_OFF
            else:
                color = NODE
            pygame.draw.circle(t.screen, color, point, 4)
            if node in metrics.cuts:
                pygame.draw.circle(t.screen, GOLD, point, 7, 1)
            if node == self.selected:
                pygame.draw.circle(t.screen, SELECTED, point, 10, 2)
        t.text(
            f"{len(nodes)} nodes / {len(metrics.components)} components", 745, 232, t.small, GOLD, width=186
        )
        t.text(f"{len(metrics.cuts)} cut points", 745, 258, t.body)
        t.text(f"{len(metrics.bridges)} bridge links", 745, 281, t.body)
        if self.selected in nodes:
            self._draw_node_details(graph, metrics, supplied, paths)
        else:
            t.paragraph(
                "Click a node to inspect it. Select a unit on the map first to inspect its land or "
                "naval route.",
                745,
                326,
                180,
                10,
            )
        t.text(
            "Amber rings: cut points / Gold edges: bridges / Blue: selected route",
            270,
            613,
            t.small,
            DIM,
            width=656,
        )
        t.text(
            "Supply: green = supplied, red = cut off. Topological importance is not a combat bonus.",
            270,
            635,
            t.small,
            DIM,
            width=656,
        )

    def _draw_node_details(self, graph, metrics, supplied, paths) -> None:
        t = self.theme
        state = self.game.state
        node = self.selected
        if node in state.provinces:
            name = state.provinces[node].name
        else:
            name = self.game.renderer.map.seas.get(node, {}).get("name", node)
        t.text(name, 745, 323, t.heading, GOLD, width=185)
        neighbors = [n for n, _ in graph.neighbors(node) if n in metrics.nodes]
        info = [node, f"{len(neighbors)} neighbors", f"Component size: {len(metrics.component_of(node))}"]
        if self.layer == "supply":
            info.append("Supplied from a hub" if node in supplied else "No connected supply hub")
        if paths:
            info.append(
                f"Move cost: {paths.costs[node]:.2f}" if node in paths.costs else "Beyond selected unit reach"
            )
        if node in metrics.cuts:
            info.append("Potential choke point")
        t.paragraph("\n".join(info), 745, 358, 181, 9)
