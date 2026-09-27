import unittest

import pygame

from cars.ui.kit.grid import draw_grid
from cars.ui.kit.table import Column, Table
from cars.ui.kit.ui import Ui, default_scale
from tests.support import SCREEN_SIZE


class KitTestCase(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.ui = Ui(self.screen)
        self.mouse = (-100, -100)
        self.ui.mouse = lambda: self.mouse

    def tearDown(self):
        pygame.quit()


class UiTests(KitTestCase):
    def test_default_scale_suits_the_window(self):
        self.assertEqual(default_scale(780), 1.0)
        self.assertEqual(default_scale(1080), 1.25)
        self.assertEqual(default_scale(1440), 1.5)
        self.assertEqual(default_scale(2160), 2.0)

    def test_sizes_follow_the_scale(self):
        small = self.ui.font(15).get_height()
        self.ui.set_scale(2.0)
        self.assertEqual(self.ui.px(10), 20)
        self.assertGreater(self.ui.font(15).get_height(), small * 1.7)

    def test_long_text_is_trimmed(self):
        font = self.ui.font(15)
        text = self.ui.fit("A very long line of text indeed", font, 80)
        self.assertTrue(text.endswith("…"))
        self.assertLessEqual(font.size(text)[0], 80)

    def test_panels_return_their_inner_area(self):
        rect = pygame.Rect(100, 100, 300, 200)
        inner = self.ui.panel(rect, "Title")
        self.assertTrue(rect.contains(inner))
        self.assertGreater(inner.y, rect.y + 30)


class TooltipTests(KitTestCase):
    def test_help_appears_after_a_delay_and_stays_on_screen(self):
        tips = self.ui.tips
        for self.mouse in ((5, 5), (1195, 5), (5, 775), (1195, 775)):
            tips.begin()
            self.ui.hint(pygame.Rect(0, 0, 1200, 780), "Title", "Words " * 120)
            tips.draw(self.ui, now=0)
            self.assertIsNone(tips.last_rect)
            tips.draw(self.ui, now=1000)
            self.assertTrue(self.screen.get_rect().contains(tips.last_rect))
            tips.key = None

    def test_begin_forgets_hidden_help(self):
        self.mouse = (50, 50)
        self.ui.hint(pygame.Rect(0, 0, 100, 100), "Title", "Body")
        self.ui.tips.begin()
        self.ui.tips.draw(self.ui, force=True)
        self.assertIsNone(self.ui.tips.last_rect)


class TableTests(KitTestCase):
    def setUp(self):
        super().setUp()
        self.table = Table(
            [Column("Name", lambda r: r[0]), Column("Size", lambda r: r[1], width=80, align="right")]
        )
        self.rows = [(f"row {i:02}", i % 7) for i in range(40)]
        self.rect = pygame.Rect(0, 0, 400, 300)

    def click(self, point):
        return self.table.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point), self.ui)

    def test_sorting_by_a_header(self):
        self.table.draw(self.ui, self.rect, self.rows)
        self.assertEqual(self.click(self.table._header[1].center), ("sort", 1))
        self.table.draw(self.ui, self.rect, self.rows)
        self.assertEqual(self.table.rows[0][1], 0)
        self.click(self.table._header[1].center)
        self.table.draw(self.ui, self.rect, self.rows)
        self.assertEqual(self.table.rows[0][1], 6)

    def test_scrolling_and_row_clicks(self):
        self.table.draw(self.ui, self.rect, self.rows)
        self.mouse = self.rect.center
        self.table.handle(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-2), self.ui)
        self.table.draw(self.ui, self.rect, self.rows)
        self.assertGreater(self.table.scroll, 0)
        line, row = self.table._row_rects[1]
        self.assertEqual(self.click(line.center), ("row", row))


class GridTests(KitTestCase):
    def test_height_and_cell_painters(self):
        painted = []
        rows = [["a", ("b", (200, 0, 0)), painted.append] for _ in range(3)]
        height = draw_grid(
            self.ui, 0, 0, 300, [("A", None, "left"), ("B", 60, "right"), ("", 40, "left")], rows
        )
        self.assertEqual(len(painted), 3)
        self.assertEqual(height, self.ui.px(30 - 4) + 3 * self.ui.px(30))


if __name__ == "__main__":
    unittest.main()
