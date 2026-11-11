import importlib.util
import sys
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import outfit


class OutfitSelectionTests(unittest.TestCase):
    def setUp(self):
        self.root = APP.parents[1]
        self.selection = outfit.json.loads((self.root / "evaluation/manifests/first-outfit.selection.json").read_text(encoding="utf-8"))

    def test_two_distinct_source_types_are_kept(self):
        # Actual private inputs may be absent in a fresh checkout.
        if not (self.root / self.selection["avatar"]["image"]).exists():
            self.skipTest("Private image inputs not present")
        items = outfit.validate_selection(self.selection, self.root)
        self.assertEqual({i["garment_photo_type"] for i in items}, {"model", "flat-lay"})

    def test_profile_is_not_fixed_to_first_user(self):
        if not (self.root / self.selection["avatar"]["image"]).exists():
            self.skipTest("Private image inputs not present")
        self.selection["avatar"].update(height_cm=162, weight_kg=72)
        self.assertEqual(len(outfit.validate_selection(self.selection, self.root)), 2)

    def test_nonfinite_profile_rejected(self):
        self.selection["avatar"]["height_cm"] = float("nan")
        with self.assertRaises(ValueError):
            outfit.validate_selection(self.selection, self.root)

    def test_source_file_change_rejected(self):
        if not (self.root / self.selection["avatar"]["image"]).exists():
            self.skipTest("Private image inputs not present")
        self.selection["items"][0]["image_sha256"] = "incorrect"
        with self.assertRaises(ValueError):
            outfit.validate_selection(self.selection, self.root)


class GuidanceTests(unittest.TestCase):
    def test_sequential_cfg_matches_upstream_batch_semantics(self):
        if importlib.util.find_spec("fashn_vton") is None:
            self.skipTest("Run in the installed model environment")
        import torch
        from fashn_vton.tryon_mmdit import TryOnModel

        class ForwardFixture:
            def forward(self, image, times, *, condition, mask):
                return {"x": image + times[:, None] + condition * mask[:, None]}

        fixture = ForwardFixture()
        image = torch.arange(6, dtype=torch.float32).reshape(2, 3)
        args = (image, torch.tensor([0.2, 0.8]))
        kwargs = {"condition": torch.full((2, 3), 5.0), "unused": None}
        expected = TryOnModel.forward_for_cfg(fixture, *args, **kwargs)
        actual = outfit.sequential_cfg(fixture, *args, **kwargs)
        for branch in ("v_c", "v_u"):
            torch.testing.assert_close(actual[branch], expected[branch], rtol=0, atol=0)


if __name__ == "__main__":
    unittest.main()
