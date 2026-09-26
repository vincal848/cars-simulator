"""Structural graph analysis for the strategy inspector (Tarjan's algorithm).

A bridge is an edge whose removal disconnects its component; an articulation
("cut") point is such a node. Both are topology hints, not combat modifiers.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from cars.sim.graph import Graph


@dataclass
class Topology:
    nodes: set[str]
    components: list[set[str]] = field(default_factory=list)
    cuts: set[str] = field(default_factory=set)
    bridges: set[tuple[str, str]] = field(default_factory=set)

    def component_of(self, node: str) -> set[str]:
        return next(component for component in self.components if node in component)


def analyze(graph: Graph, allowed: Iterable[str] | None = None) -> Topology:
    """Components, cut points and bridges of ``graph`` restricted to ``allowed`` nodes."""
    nodes = set(graph.adj) if allowed is None else set(allowed) & set(graph.adj)
    result = Topology(nodes)
    discovered: dict[str, int] = {}
    low: dict[str, int] = {}

    def visit(node: str, parent: str | None, component: set[str]) -> None:
        discovered[node] = low[node] = len(discovered)
        component.add(node)
        children = 0
        for neighbor, _ in graph.neighbors(node):
            if neighbor not in nodes:
                continue
            if neighbor not in discovered:
                children += 1
                visit(neighbor, node, component)
                low[node] = min(low[node], low[neighbor])
                if parent is not None and low[neighbor] >= discovered[node]:
                    result.cuts.add(node)
                if low[neighbor] > discovered[node]:
                    result.bridges.add(tuple(sorted((node, neighbor))))
            elif neighbor != parent:
                low[node] = min(low[node], discovered[neighbor])
        if parent is None and children > 1:
            result.cuts.add(node)

    for node in sorted(nodes):
        if node not in discovered:
            component: set[str] = set()
            visit(node, None, component)
            result.components.append(component)
    return result
