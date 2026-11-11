import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app/experiment.py"
spec = importlib.util.spec_from_file_location("experiment", APP)
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)
ROOT = APP.parents[2]


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.manifest = json.loads((ROOT / "evaluation/manifests/trendyol-10.template.json").read_text(encoding="utf-8"))
        self.manifest["person"]["consent_confirmed"] = True
        for entry in [self.manifest["person"], *self.manifest["cases"]]:
            path = self.root / entry["image"]
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b"fixture: validation only, not an image")
        for case in self.manifest["cases"]:
            case.update(product_url="https://www.trendyol.com/test/urun-p-12345",
                        source_image_url="https://example.org/test-fixture.jpg", source_notes="front")

    def test_selected_case_does_not_require_other_garments(self):
        (self.root / self.manifest["cases"][0]["image"]).unlink()
        selected = experiment.validate_manifest(self.manifest, self.root, ["tshirt"])
        self.assertEqual([c["id"] for c in selected], ["tshirt"])

    def test_consent_required(self):
        self.manifest["person"]["consent_confirmed"] = False
        with self.assertRaises(ValueError):
            experiment.validate_manifest(self.manifest, self.root)

    def test_flat_lay_source_is_accepted(self):
        self.manifest["cases"][0]["garment_photo_type"] = "flat-lay"
        self.assertEqual(experiment.validate_manifest(self.manifest, self.root)[0]["garment_photo_type"], "flat-lay")

    def test_wrong_domain_rejected(self):
        self.manifest["cases"][0]["product_url"] = "https://trendyol.com.evil.example/urun-p-1"
        with self.assertRaises(ValueError):
            experiment.validate_manifest(self.manifest, self.root)

    def test_path_escape_rejected(self):
        self.manifest["person"]["image"] = "../private.jpg"
        with self.assertRaises(ValueError):
            experiment.validate_manifest(self.manifest, self.root)

    def test_missing_and_duplicate_cases_rejected(self):
        with self.assertRaises(ValueError):
            experiment.validate_manifest(self.manifest, self.root, ["missing"])
        self.manifest["cases"][1]["id"] = self.manifest["cases"][0]["id"]
        with self.assertRaises(ValueError):
            experiment.validate_manifest(self.manifest, self.root)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.cases = [{"id": f"case-{i}", "status": "completed"} for i in range(10)]
        self.record = {"cases": self.cases}
        experiment.write_json(self.root / "run.json", self.record)
        experiment.write_json(self.root / "manifest.json", {"cases": self.cases})
        self.rows = [{"id": c["id"], "reviewer": "test reviewer", "critical_failure": "no",
                      "notes": "unit test, no AI image", **{m: "3" for m in experiment.METRICS}}
                     for c in self.cases]

    def review(self):
        with (self.root / "review.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
            writer.writeheader()
            writer.writerows(self.rows)
        return experiment.evaluate(self.root)

    def test_blank_review_never_passes(self):
        experiment.create_review(self.root, self.record)
        summary = experiment.evaluate(self.root)
        self.assertEqual(summary["quality_gate"], "pending")
        self.assertEqual(summary["passed"], 0)

    def test_critical_failure_overrides_high_scores(self):
        for row in self.rows[:3]:
            row["critical_failure"] = "yes"
        self.assertEqual(self.review()["quality_gate"], "failed")

    def test_unselected_clothes_change_vetoes_high_garment_scores(self):
        for row in self.rows:
            row["untargeted_changes"] = "no"
        for row in self.rows[:3]:
            row["untargeted_changes"] = "yes"
        self.assertEqual(self.review()["quality_gate"], "failed")

    def test_failed_generation_counts_in_denominator(self):
        for case in self.cases[:2]:
            case["status"] = "failed"
        experiment.write_json(self.root / "run.json", self.record)
        summary = self.review()
        self.assertEqual(summary["passed"], 8)
        self.assertEqual(summary["quality_gate"], "passed")
        self.assertEqual(summary["decisions"][0]["decision"], "not_generated")

    def test_missing_review_does_not_become_zero_or_pass(self):
        self.rows.pop()
        self.assertEqual(self.review()["quality_gate"], "pending")

    def test_invalid_score_remains_unreviewed(self):
        self.rows[0]["face"] = "5"
        self.assertEqual(self.review()["decisions"][0]["decision"], "not_reviewed")

    def test_single_case_cannot_pass_full_suite(self):
        self.record["cases"] = self.cases[:1]
        experiment.write_json(self.root / "run.json", self.record)
        self.assertEqual(self.review()["quality_gate"], "pending")

    def test_duplicate_review_rejected(self):
        self.rows.append(self.rows[0])
        with self.assertRaises(ValueError):
            self.review()

    def test_html_escapes_reviewer_notes(self):
        self.rows[0]["notes"] = "<script>alert('x')</script>"
        self.review()
        output = (self.root / "report.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)


class NotebookTests(unittest.TestCase):
    def test_all_python_cells_compile_and_embedded_runner_is_current(self):
        notebook = json.loads((ROOT / "notebooks/TryFitNext_FASHN_Quality_Test.ipynb").read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), f"cell-{index}", "exec")
                self.assertEqual(cell["outputs"], [])
        self.assertIn(repr(APP.read_text(encoding="utf-8")), "".join(notebook["cells"][3]["source"]))


if __name__ == "__main__":
    unittest.main()
