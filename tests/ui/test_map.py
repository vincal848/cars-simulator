import unittest
from unittest.mock import patch

import pygame

from cars.sim.entities import Unit
from cars.ui.camera import Camera, point_in_polygon
from cars.ui.kit.ui import Ui
from cars.ui.map.labels import layout_labels
from cars.ui.map.map_view import MapView, Scene
from cars.ui.map.relief import relief_image
from tests.support import SCREEN_SIZE, detailed


class CameraTests(unittest.TestCase):
    def test_wrapping_and_latitude_limits(self):
        camera = Camera(pygame.Rect(0, 0, 1200, 780))
        before = camera.nearest(camera.project((-100, 30)))
        camera.pan(camera.period * 100, 0)
        self.assertAlmostEqual(before[0], camera.nearest(camera.project((-100, 30)))[0])
        # At world view the map is shorter than the viewport, so it stays centred.
        offset = camera.offset[1]
        camera.pan(0, 1e8)
        self.assertAlmostEqual(camera.offset[1], offset)
        camera.zoom(2, (600, 371))
        camera.pan(0, 1e8)
        self.assertLessEqual(camera.offset[1], 81 * camera.scale)
        camera.pan(0, -1e8)
        self.assertGreaterEqual(camera.offset[1], 780 - 62 * camera.scale)

    def test_a_bigger_window_shows_the_same_view_in_more_detail(self):
        small = Camera(pygame.Rect(0, 0, 1200, 780))
        large = Camera(pygame.Rect(0, 0, 2400, 1560))
        self.assertAlmostEqual(large.scale, small.scale * 2)
        small.zoom(2, (600, 390))
        middle = small.to_world(small.viewport.center)
        small.resize(pygame.Rect(0, 0, 1800, 1170))
        self.assertAlmostEqual(small.zoom_level, 2)
        for got, want in zip(small.to_world(small.viewport.center), middle, strict=True):
            self.assertAlmostEqual(got, want, places=4)


class MapViewTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.ui = Ui(pygame.display.set_mode(SCREEN_SIZE))
        self.state, shapes, seas = detailed()
        self.map = MapView(self.state, shapes, seas, self.ui)

    def tearDown(self):
        pygame.quit()

    def test_hit_testing_survives_panning_across_the_seam(self):
        self.map.pan(self.map.camera.period, 0)
        province = self.state.units["infantry0_0"].location
        self.assertEqual(self.map.node_at(self.map.anchors[province], "land"), province)

    def paint(self) -> pygame.Surface:
        screen = self.ui.surface
        self.map.atlas.draw(screen, self.map.origin, self.map.camera.period, self.map.viewport)
        return screen

    def test_the_painted_map_is_georeferenced(self):
        self.assertEqual(relief_image().get_size(), (4500, 4200))
        point = (-110, 40)
        before = self.paint().get_at(self.map.camera.project(point))
        self.map.pan(30, 0)
        self.assertEqual(before, self.paint().get_at(self.map.camera.project(point)))

    def test_panning_reuses_painted_tiles(self):
        self.paint()
        tiles = dict(self.map.atlas._tiles)
        self.map.pan(40, 25)
        self.paint()
        self.assertTrue(tiles)
        self.assertTrue(all(self.map.atlas._tiles[key] is tile for key, tile in tiles.items()))

    def test_labels_slide_while_dragging_and_settle_afterwards(self):
        self.map.zoom(3, (600, 370))
        screen = self.ui.surface
        self.map.draw(screen, Scene(), [], [])
        labels = self.map.labels
        first = labels[0].rect.copy()
        self.map.pan(12, 5, dragging=True)
        self.map.draw(screen, Scene(), [], [])
        self.assertIs(self.map.labels, labels)
        self.assertEqual(labels[0].rect.topleft, (first.x + 12, first.y + 5))
        self.map.draw(screen, Scene(), [], [])  # The drag has stopped.
        self.assertIsNot(self.map.labels, labels)

    def test_each_stack_gets_one_marker_that_steps_off_towns(self):
        lead = self.state.units["infantry0_0"]
        for i in range(2):
            self.state.units[f"extra{i}"] = Unit(f"extra{i}", lead.owner, lead.location, hp=5)
        calls = []

        def record(*args, **_options):
            calls.append(args)
            return pygame.Rect(0, 0, 1, 1)

        with patch("cars.ui.map.map_view.draw_army", record):
            self.map.draw(self.ui.surface, Scene(), [], [])
        units = [u for u in self.state.units.values() if u.location == lead.location and u.is_land]
        stack = [args for args in calls if args[4] == len(units)]
        self.assertEqual(len(stack), 1)
        self.assertAlmostEqual(stack[0][5], sum(u.hp for u in units) / (10 * len(units)))
        town = self.map.city_markers[0]
        self.assertGreater(self.map._clear_of_towns(*town.point), 0)

    def test_a_captured_province_is_repainted(self):
        province = self.state.provinces[self.state.units["infantry0_0"].location]
        point = self.map.anchors[province.id]
        self.paint()
        before = self.ui.surface.get_at(point)
        province.controller = next(f for f in self.state.factions if f != province.controller)
        self.assertEqual(before, self.paint().get_at(point))  # Tiles are cached...
        self.map.draw(self.ui.surface, Scene(), [], [])  # ...until the map notices.
        self.assertNotEqual(before, self.paint().get_at(point))

    def test_labels_fit_inside_their_polygons_for_every_font(self):
        self.map.zoom(3, self.map.anchors[next(iter(self.state.provinces))])
        for index in range(3):
            self.ui.set_font(index)
            labels = layout_labels(self.map, self.ui, [])
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
