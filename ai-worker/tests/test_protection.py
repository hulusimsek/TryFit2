import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
AVAILABLE = all(importlib.util.find_spec(name) for name in ("numpy", "cv2", "PIL"))


@unittest.skipUnless(AVAILABLE, "Run inside the model environment")
class PreservationTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        from PIL import Image
        self.np = np
        self.first = Image.new("RGB", (20, 20), (200, 20, 30))
        self.second = Image.new("RGB", (20, 20), (10, 40, 220))
        self.labels = np.zeros((20, 20), dtype=np.uint8)
        self.labels[5:15, 5:15] = 3

    def test_top_interior_comes_from_first_stage(self):
        from protect_outfit import protect_upper
        image, _ = protect_upper(self.first, self.second, self.labels)
        self.assertEqual(image.getpixel((10, 10)), self.first.getpixel((10, 10)))

    def test_lower_clothing_comes_from_second_stage(self):
        from protect_outfit import protect_upper
        self.labels[:] = 6  # pants should never be protected from the first stage
        image, _ = protect_upper(self.first, self.second, self.labels)
        self.np.testing.assert_array_equal(self.np.asarray(image), self.np.asarray(self.second))

    def test_different_geometry_cannot_be_silently_composited(self):
        from protect_outfit import protect_upper
        with self.assertRaises(ValueError):
            protect_upper(self.first, self.second, self.labels[:10])


if __name__ == "__main__":
    unittest.main()
