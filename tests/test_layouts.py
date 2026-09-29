import unittest

from app.layouts import Rect, build_grid, grid_shape


class GridShapeTests(unittest.TestCase):
    def test_presets(self):
        self.assertEqual(grid_shape(2), (1, 2))
        self.assertEqual(grid_shape(3), (1, 3))
        self.assertEqual(grid_shape(4), (2, 2))
        self.assertEqual(grid_shape(6), (2, 3))
        self.assertEqual(grid_shape(8), (2, 4))
        self.assertEqual(grid_shape(9), (3, 3))

    def test_six_window_grid_stays_inside_monitor(self):
        area = Rect(0, 0, 1920, 1040)
        cells = build_grid(area, 6, margin=16, gap=12)
        self.assertEqual(len(cells), 6)
        for cell in cells:
            self.assertGreater(cell.width, 0)
            self.assertGreater(cell.height, 0)
            self.assertGreaterEqual(cell.x, area.x)
            self.assertGreaterEqual(cell.y, area.y)
            self.assertLessEqual(cell.x + cell.width, area.x + area.width)
            self.assertLessEqual(cell.y + cell.height, area.y + area.height)

    def test_negative_monitor_coordinates_are_supported(self):
        area = Rect(-1920, 0, 1920, 1080)
        cells = build_grid(area, 4, margin=10, gap=8)
        self.assertEqual(len(cells), 4)
        self.assertLess(cells[0].x, 0)
        self.assertLessEqual(cells[-1].x + cells[-1].width, 0)

    def test_custom_shape(self):
        area = Rect(100, 50, 1600, 900)
        cells = build_grid(area, 6, margin=20, gap=10, custom_shape=(3, 2))
        self.assertEqual(len(cells), 6)
        self.assertEqual(cells[0].x, 120)
        self.assertEqual(cells[0].y, 70)
        self.assertGreater(cells[2].y, cells[0].y)

    def test_large_spacing_never_creates_zero_size_cells(self):
        area = Rect(0, 0, 200, 120)
        cells = build_grid(area, 6, margin=60, gap=50)
        self.assertEqual(len(cells), 6)
        self.assertTrue(all(cell.width >= 1 and cell.height >= 1 for cell in cells))


if __name__ == "__main__":
    unittest.main()
