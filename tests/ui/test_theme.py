import unittest

import pygame

from cars.ui.art.badges import badge
from cars.ui.display import OFF_CANVAS, Display
from cars.ui.theme import Theme
from tests.support import SCREEN_SIZE


class ThemeTestCase(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.theme = Theme(self.screen)

    def tearDown(self):
        pygame.quit()


class TooltipTests(ThemeTestCase):
    def test_help_appears_after_a_delay_and_resets(self):
        tips = self.theme.tips
        self.theme.mouse_pos = lambda: (50, 50)
        self.theme.hint((20, 20, 80, 80), "Roads", "Lower terrain costs per level.")
        tips.draw(self.theme, now=100)
        self.assertIsNone(tips.last_rect)
        tips.draw(self.theme, now=451)
        self.assertIsNotNone(tips.last_rect)
        tips.begin()
        tips.draw(self.theme, now=500)
        self.assertIsNone(tips.last_rect)
        self.assertIsNone(tips.key)

    def test_long_help_stays_on_screen_in_every_corner(self):
        for point in ((1, 1), (1199, 1), (1, 779), (1199, 779)):
            self.theme.mouse_pos = lambda point=point: point
            self.theme.tips.begin()
            self.theme.hint(
                (0, 0, 1200, 780), "Supply and control", "Long explanatory text. " * 8 + " X" * 40
            )
            self.theme.tips.draw(self.theme, force=True)
            self.assertTrue(self.screen.get_rect().contains(self.theme.tips.last_rect))

    def test_modal_panels_clear_hidden_help(self):
        self.theme.mouse_pos = lambda: (40, 40)
        self.theme.hint((0, 0, 100, 100), "Hidden underlying panel", "Old text")
        self.theme.tips.begin()
        self.theme.tips.draw(self.theme, force=True)
        self.assertIsNone(self.theme.tips.last_rect)


class InsigniaTests(ThemeTestCase):
    def test_service_insignia_are_distinct_and_cached(self):
        icons = {pygame.image.tobytes(badge(kind, 28), "RGBA") for kind in ("land", "naval", "air", "supply")}
        self.assertEqual(len(icons), 4)
        self.assertIs(badge("naval", 28), badge("naval", 28))


class DisplayTests(unittest.TestCase):
    def test_toggle_and_pointer_mapping(self):
        pygame.init()
        display = Display()
        display.toggle()
        self.assertTrue(display.borderless)
        for size in ((1920, 1080), (1024, 768), (2560, 1080)):
            display.viewport = display.canvas.get_rect().fit(pygame.Rect((0, 0), size))
            center = display.viewport.center
            self.assertLessEqual(abs(display.point(center)[0] - 600), 1)
            self.assertLessEqual(abs(display.point(center)[1] - 390), 1)
            event = display.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=center, button=1))
            self.assertEqual(event.pos, display.point(center))
            self.assertEqual(display.point((-1, -1)), OFF_CANVAS)
        display.toggle()
        self.assertFalse(display.borderless)
        desktop = pygame.display.get_desktop_sizes()[0]
        self.assertEqual(display.window.get_size(), (min(1200, desktop[0] - 60), min(780, desktop[1] - 90)))
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
