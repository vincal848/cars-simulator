"""Undirected weighted graphs. Geometry never reaches this layer; nodes are string IDs."""

from collections.abc import Callable, ItemsView, Iterable
from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf

Weight = Callable[[str, str, "Edge"], float]


@dataclass(frozen=True)
class Edge:
    base_cost: float = 1
    river_crossing: str | None = None
    mountain_pass: bool = False
    infrastructure: int = 0
    border_type: str = "open"


@dataclass
class Paths:
    """Result of a shortest-path search: cost to each reached node and its predecessor."""

    costs: dict[str, float]
    parents: dict[str, str]

    def path(self, destination: str) -> list[str]:
        if destination not in self.costs:
            return []
        path = [destination]
        while path[-1] in self.parents:
            path.append(self.parents[path[-1]])
        return path[::-1]


class Graph:
    def __init__(self) -> None:
        self.adj: dict[str, dict[str, Edge]] = {}

    def __contains__(self, node: object) -> bool:
        return node in self.adj

    def nodes(self) -> list[str]:
        return list(self.adj)

    def add_node(self, node: str) -> None:
        self.adj.setdefault(node, {})

    def connect(self, a: str, b: str, edge: Edge | None = None) -> None:
        edge = edge or Edge()
        if edge.base_cost <= 0:
            raise ValueError("Edges require positive base costs")
        self.add_node(a)
        self.add_node(b)
        self.adj[a][b] = self.adj[b][a] = edge

    def edge(self, a: str, b: str) -> Edge:
        return self.adj[a][b]

    def neighbors(self, node: str) -> ItemsView[str, Edge]:
        return self.adj.get(node, {}).items()

    def edges(self) -> Iterable[tuple[str, str, Edge]]:
        """Each undirected edge once, as ``(a, b, edge)`` with ``a < b``."""
        for a in self.adj:
            for b, edge in self.neighbors(a):
                if a < b:
                    yield a, b, edge

    def shortest_paths(
        self,
        start: str,
        weight: Weight,
        budget: float = inf,
        expand: Callable[[str], bool] | None = None,
    ) -> Paths:
        """Dijkstra from ``start``, stopping at ``budget``.

        Nodes rejected by ``expand`` can be reached but not passed through, which is
        how hostile provinces end a route.
        """
        costs, parents = {start: 0.0}, {}
        queue = [(0.0, start)]
        while queue:
            cost, node = heappop(queue)
            if cost != costs[node]:
                continue
            if node != start and expand is not None and not expand(node):
                continue
            for neighbor, edge in self.neighbors(node):
                step = weight(node, neighbor, edge)
                if step < 0:
                    raise ValueError("Dijkstra requires nonnegative weights")
                candidate = cost + step
                if candidate <= budget and candidate < costs.get(neighbor, inf):
                    costs[neighbor] = candidate
                    parents[neighbor] = node
                    heappush(queue, (candidate, neighbor))
        return Paths(costs, parents)

    def reachable_from(self, sources: Iterable[str], allowed: Callable[[str], bool]) -> set[str]:
        """Every node connected to ``sources`` through nodes that satisfy ``allowed``."""
        seen = {source for source in sources if allowed(source)}
        pending = list(seen)
        while pending:
            for neighbor, _ in self.neighbors(pending.pop()):
                if neighbor not in seen and allowed(neighbor):
                    seen.add(neighbor)
                    pending.append(neighbor)
        return seen


def step_cost(_a: str, _b: str, edge: Edge) -> float:
    """Weight function for layers that use the edge's base cost unchanged."""
    return edge.base_cost
