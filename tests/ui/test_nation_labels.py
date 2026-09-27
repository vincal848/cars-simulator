import unittest

import pygame

from cars.ui.map.geometry import province_polygons
from cars.ui.map.nation_labels import NationNames, render, territories
from cars.ui.typography import DEFAULT_FONT, TITLE, load_font
from tests.support import compact


def box(west, south, east, north):
    return [[[(west, south), (east, south), (east, north), (west, north), (west, south)]]]


class NationLabelTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.fonts = {}

    def tearDown(self):
        pygame.quit()

    def font(self, size):
        return self.fonts.setdefault(size, load_font(DEFAULT_FONT, size, TITLE))

    def test_a_wide_territory_is_named_along_its_length(self):
        (curve,) = territories([box(-120, 30, -80, 45)])
        self.assertAlmostEqual(abs(curve.axis[0]), 1, places=2)
        lettering = render("Wide Dominion", curve, 6, self.font)
        self.assertIsNotNone(lettering)
        _, rect = lettering
        self.assertGreater(rect.width, rect.height * 3)

    def test_separate_islands_are_separate_territories(self):
        curves = territories([box(-120, 30, -100, 40), box(-90, 30, -70, 40)])
        self.assertEqual(len(curves), 2)

    def test_a_territory_too_small_for_its_name_goes_unnamed(self):
        (curve,) = territories([box(-100, 30, -97, 33)])
        self.assertIsNone(render("An Exceedingly Long Name", curve, 4.4, self.font))

    def test_names_follow_conquests(self):
        state, shapes, _ = compact()
        geometry = {p.id: province_polygons(shapes[p.shape_id]) for p in state.provinces.values()}
        names = NationNames(state, geometry)
        names.curves()
        before = dict(names._curves)
        state.provinces["cascadia"].controller = "f1"
        names.curves()
        changed = {key[0] for key in names._curves if key not in before}
        self.assertEqual(changed, {"f0", "f1"})
