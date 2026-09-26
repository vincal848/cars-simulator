import unittest

from cars.sim.graph import Edge, Graph, step_cost
from cars.sim.topology import analyze


class ShortestPathTests(unittest.TestCase):
    def test_cheapest_route_within_budget(self):
        graph = Graph()
        graph.connect("a", "b", Edge(4))
        graph.connect("a", "c", Edge(1))
        graph.connect("c", "b", Edge(1))
        graph.connect("b", "d", Edge(1))
        paths = graph.shortest_paths("a", step_cost, budget=2)
        self.assertEqual(paths.path("b"), ["a", "c", "b"])
        self.assertEqual(paths.costs["b"], 2)
        self.assertNotIn("d", paths.costs)
        self.assertEqual(paths.path("d"), [])

    def test_blocked_nodes_can_be_entered_but_not_crossed(self):
        graph = Graph()
        graph.connect("a", "wall")
        graph.connect("wall", "beyond")
        paths = graph.shortest_paths("a", step_cost, expand=lambda node: node != "wall")
        self.assertIn("wall", paths.costs)
        self.assertNotIn("beyond", paths.costs)

    def test_rejects_non_positive_edges(self):
        with self.assertRaises(ValueError):
            Graph().connect("a", "b", Edge(0))

    def test_connectivity_respects_allowed_nodes(self):
        graph = Graph()
        graph.connect("hub", "bridge")
        graph.connect("bridge", "army")
        self.assertIn("army", graph.reachable_from(["hub"], lambda _node: True))
        self.assertNotIn("army", graph.reachable_from(["hub"], lambda node: node != "bridge"))

    def test_edges_are_listed_once(self):
        graph = Graph()
        graph.connect("a", "b")
        graph.connect("b", "c")
        self.assertEqual([(a, b) for a, b, _ in graph.edges()], [("a", "b"), ("b", "c")])


class TopologyTests(unittest.TestCase):
    def test_chain_cycle_and_disconnected_metrics(self):
        graph = Graph()
        graph.connect("a", "b")
        graph.connect("b", "c")
        graph.add_node("island")
        topology = analyze(graph)
        self.assertEqual(topology.cuts, {"b"})
        self.assertEqual(len(topology.bridges), 2)
        self.assertEqual(len(topology.components), 2)
        self.assertEqual(topology.component_of("a"), {"a", "b", "c"})

        graph.connect("a", "c")
        topology = analyze(graph)
        self.assertFalse(topology.cuts)
        self.assertFalse(topology.bridges)
        self.assertEqual(analyze(graph, {"a", "island"}).nodes, {"a", "island"})


if __name__ == "__main__":
    unittest.main()
