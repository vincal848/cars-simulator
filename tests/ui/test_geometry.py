import unittest

from cars.ui.map.geometry import borders

# Two unit squares side by side: they share the edge x = 1.
LEFT = [[[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]]]
RIGHT = [[[(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]]]


class BorderTests(unittest.TestCase):
    def test_shared_edges_are_borders_and_the_rest_is_coast(self):
        lines = {border.provinces: border for border in borders({"left": LEFT, "right": RIGHT})}
        self.assertEqual(set(lines), {("left",), ("right",), ("left", "right")})
        self.assertFalse(lines[("left", "right")].is_coast)
        self.assertEqual(sorted(lines[("left", "right")].line), [(1, 0), (1, 1)])
        self.assertTrue(lines[("left",)].is_coast)

    def test_coasts_are_chained_into_single_polylines(self):
        lines = {border.provinces: border for border in borders({"left": LEFT, "right": RIGHT})}
        # Three coastal edges of the left square, joined end to end.
        self.assertEqual(len(lines[("left",)].line), 4)
