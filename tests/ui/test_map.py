import unittest

import pygame

from cars.ui.camera import Camera, point_in_polygon
from cars.ui.map.labels import layout_labels
from cars.ui.map.map_view import MapView
from cars.ui.map.relief import relief_image
from cars.ui.palette import MAP_AREA
from cars.ui.theme import Theme
from tests.support import SCREEN_SIZE, detailed


class CameraTests(unittest.TestCase):
    def test_wrapping_and_latitude_limits(self):
        camera = Camera()
        before = camera.nearest(camera.project((-100, 30)))
        camera.pan(camera.period * 100, 0)
        self.assertAlmostEqual(before[0], camera.nearest(camera.project((-100, 30)))[0])
        # At world view the map is shorter than the viewport, so it stays centred.
        camera.pan(0, 1e8)
        self.assertAlmostEqual(camera.offset[1], (MAP_AREA.height + 19 * camera.scale) / 2)
        camera.zoom(2, (600, 371))
        camera.pan(0, 1e8)
        self.assertLessEqual(camera.offset[1], 81 * camera.scale)
        camera.pan(0, -1e8)
        self.assertGreaterEqual(camera.offset[1], MAP_AREA.height - 62 * camera.scale)


class MapViewTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.theme = Theme(pygame.display.set_mode(SCREEN_SIZE))
        self.state, shapes, seas = detailed()
        self.map = MapView(self.state, shapes, seas, self.theme)

    def tearDown(self):
        pygame.quit()

    def test_hit_testing_survives_panning_across_the_seam(self):
        self.map.pan(self.map.camera.period, 0)
        province = self.state.units["infantry0_0"].location
        self.assertEqual(self.map.node_at(self.map.anchors[province], "land"), province)

    def test_relief_is_georeferenced(self):
        self.assertEqual(relief_image().get_size(), (4500, 4200))
        point = (-110, 40)
        before = self.map.relief_surface.get_at(self.map.camera.project(point))
        self.map.pan(30, 0)
        self.assertEqual(before, self.map.relief_surface.get_at(self.map.camera.project(point)))

    def test_labels_fit_inside_their_polygons_for_every_font(self):
        self.map.zoom(3, self.map.anchors[next(iter(self.state.provinces))])
        theme = self.theme
        for index in range(3):
            theme.set_font(index)
            labels = layout_labels(self.map, theme.font, [])
            self.assertTrue(labels)
            for label in labels:
                rect = label.rect
                corners = [
                    rect.topleft,
                    (rect.right - 1, rect.top),
                    (rect.left, rect.bottom - 1),
                    (rect.right - 1, rect.bottom - 1),
                ]
                self.assertTrue(
                    any(
                        all(
                            point_in_polygon(p, rings[0])
                            and not any(point_in_polygon(p, h) for h in rings[1:])
                            for p in corners
                        )
                        for rings in self.map.parts[label.province]
                    )
                )
                self.assertLessEqual(max(label.font.size(line)[0] for line in label.lines), rect.width)


if __name__ == "__main__":
    unittest.main()
