import csv
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image

APP_DIR = Path(__file__).resolve().parents[1] / "app"
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP_DIR))

from experiment import sha256  # noqa: E402
import local_skirt  # noqa: E402
import pilot_runner  # noqa: E402


class FakeParser:
    def __init__(self, target_labels_by_sha):
        self.target_labels_by_sha = target_labels_by_sha
        self.calls = 0

    def predict(self, image):
        self.calls += 1
        arr = np.asarray(image)
        h, w = arr.shape[:2]
        # Allow target-specific masks by top-left pixel RGB tag; fallback to valid full parsing.
        key = tuple(int(v) for v in arr[0, 0])
        if key in self.target_labels_by_sha:
            return self.target_labels_by_sha[key](h, w)
        labels = np.zeros((h, w), dtype="uint8")
        labels[5:35, 10:50] = 3
        labels[35:60, 10:50] = 6
        labels[60:68, 12:48] = 14
        labels[68:76, 12:48] = 15
        labels[25:42, 4:9] = 13
        return labels


class FakeFashnPipeline:
    def __init__(self, target_labels_by_sha=None, *, top_tag_override=None):
        self.hp_model = FakeParser(target_labels_by_sha or {})
        self.top_tag_override = top_tag_override or {}
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        person = kwargs["person_image"]
        key = person.getpixel((0, 0))
        color = self.top_tag_override.get(key, key) if kwargs["category"] == "tops" else (30, 80, 140)
        if kwargs["category"] == "bottoms":
            # Preserve RGB tag in corner so post-top checks see target parsing profile.
            out = Image.new("RGB", person.size, (30, 80, 140))
            out.putpixel((0, 0), key)
        else:
            out = Image.new("RGB", person.size, color)
        return SimpleNamespace(images=[out])


def _full_labels(h, w):
    labels = np.zeros((h, w), dtype="uint8")
    labels[5:35, 10:50] = 3
    labels[35:60, 10:50] = 6
    labels[60:68, 12:48] = 14
    labels[68:76, 12:48] = 15
    labels[25:42, 4:9] = 13
    return labels


def _no_feet_labels(h, w):
    labels = _full_labels(h, w)
    labels[labels == 15] = 0
    return labels


def _no_upper_labels(h, w):
    labels = _full_labels(h, w)
    labels[labels == 3] = 0
    return labels


def _no_lower_labels(h, w):
    labels = _full_labels(h, w)
    labels[np.isin(labels, [5, 6, 7, 14])] = 0
    return labels


def _invalid_range_labels(h, w):
    return np.full((h, w), 99, dtype="uint8")


class RaisingStage2Pipeline(FakeFashnPipeline):
    def __init__(self, bottom_error, target_labels_by_sha=None):
        super().__init__(target_labels_by_sha=target_labels_by_sha)
        self.bottom_error = bottom_error

    def __call__(self, **kwargs):
        if kwargs["category"] == "bottoms":
            raise self.bottom_error
        return super().__call__(**kwargs)


def _build_fixture_repo(root: Path):
    (root / "runs").mkdir(parents=True, exist_ok=True)
    data_dir = root / "data/pilot"
    data_dir.mkdir(parents=True, exist_ok=True)

    target_colors = [
        ("pilot-target-1", "slender", (210, 100, 100)),
        ("pilot-target-2", "medium", (100, 210, 100)),
        ("pilot-target-3", "fuller", (100, 100, 210)),
    ]
    targets = []
    for index, (tid, group, color) in enumerate(target_colors, start=1):
        img_path = data_dir / f"target-{index}.png"
        Image.new("RGB", (60, 80), color).save(img_path)
        targets.append(
            {
                "id": tid,
                "image": img_path.relative_to(root).as_posix(),
                "image_sha256": sha256(img_path),
                "adult_confirmed": True,
                "consent_confirmed": True,
                "consent_record_id": f"PILOT-CONSENT-0{index}",
                "consent_scope": pilot_runner.ALLOWED_CONSENT_SCOPE,
                "retention_until": (date.today() + timedelta(days=180)).isoformat(),
                "body_group": group,
                "measured": False,
                "pose_notes": "Full-body standing pose for fixture test",
                "footwear_notes": "Fixture footwear note",
                "current_clothing_notes": "Simple fixture top and bottom",
                "lighting_background_notes": "Fixture lighting and background",
            }
        )

    product_specs = [
        ("pilot-top", "top", "tops", (220, 40, 40)),
        ("pilot-trousers", "trousers", "bottoms", (40, 40, 220)),
        ("pilot-skirt", "skirt", "bottoms", (20, 20, 20)),
    ]
    products = []
    for pid, role, category, color in product_specs:
        img_path = data_dir / f"{pid}.png"
        Image.new("RGB", (60, 80), color).save(img_path)
        img_sha = sha256(img_path)

        ext_dir = root / "runs" / f"source-extraction-{pid}-refined"
        ext_dir.mkdir(parents=True, exist_ok=True)
        mask = np.zeros((80, 60), dtype="uint8")
        mask[15:65, 15:45] = 255
        Image.fromarray(mask).save(ext_dir / "mask.png")
        ext_meta = {
            "annotation": {"id": pid, "category": category, "image_sha256": img_sha},
            "mask_sha256": sha256(ext_dir / "mask.png"),
        }
        (ext_dir / "extraction.json").write_text(json.dumps(ext_meta), encoding="utf-8")

        products.append(
            {
                "id": pid,
                "label": f"Fixture {pid}",
                "flow_role": role,
                "category": category,
                "garment_photo_type": "model",
                "image": img_path.relative_to(root).as_posix(),
                "image_sha256": img_sha,
                "product_url": f"https://www.trendyol.com/fixture/{pid}-p-123456",
                "source_image_url": f"https://cdn.example.invalid/{pid}.jpg",
                "photo_origin": "real_model_photo",
                "listing_ai_generated_label_observed": False,
                "source_notes": f"Fixture real model {role}",
            }
        )

    manifest = {
        "schema_version": 1,
        "purpose": "Fixture 3x3 pilot manifest",
        "targets": targets,
        "products": products,
        "flows": [
            {"id": "top", "flow_type": "top_only", "top_id": "pilot-top"},
            {"id": "trousers", "flow_type": "top_plus_trousers", "top_id": "pilot-top", "bottom_id": "pilot-trousers"},
            {"id": "skirt-tucked", "flow_type": "top_plus_skirt", "top_id": "pilot-top", "bottom_id": "pilot-skirt", "tuck_top": True},
        ],
        "optional_controls": [
            {"id": "skirt-untucked", "flow_type": "top_plus_skirt", "top_id": "pilot-top", "bottom_id": "pilot-skirt", "tuck_top": False},
        ],
    }
    manifest_path = data_dir / "pilot-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest, manifest_path


def _fake_catvton_success(root: Path, run_dir: Path):
    def fake_lower(case_dir: Path):
        handoff_sha = sha256(case_dir / "skirt-handoff.json")
        repaint = case_dir / "02-skirt-repaint.png"
        raw = case_dir / "02-skirt-raw.png"
        Image.new("RGB", (60, 80), (15, 15, 15)).save(raw)
        Image.new("RGB", (60, 80), (18, 18, 18)).save(repaint)
        (case_dir / "catvton-outcome.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "raw_sha256": sha256(raw),
                    "output_sha256": sha256(repaint),
                    "handoff_sha256": handoff_sha,
                    "elapsed_seconds": 0.05,
                }
            ),
            encoding="utf-8",
        )

    pilot_runner.run_catvton_lower(root, run_dir, skirt_lower_fn=fake_lower)


class PilotValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest, self.manifest_path = _build_fixture_repo(self.root)

    def test_template_has_no_real_files_or_consent_and_is_rejected_unfilled(self):
        template_path = ROOT_DIR / "evaluation/manifests/pilot-3x3.template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        for target in template["targets"]:
            self.assertFalse(target["consent_confirmed"])
            self.assertFalse(target["adult_confirmed"])
            self.assertEqual(target["image_sha256"], "")
            self.assertEqual(target["consent_record_id"], "")
            self.assertFalse((ROOT_DIR / target["image"]).exists())
        for product in template["products"]:
            self.assertEqual(product["image_sha256"], "")
            self.assertEqual(product["product_url"], "")
            self.assertFalse((ROOT_DIR / product["image"]).exists())
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(template, ROOT_DIR)

    def test_valid_manifest_and_extractions_pass(self):
        validated = pilot_runner.validate_pilot_manifest(self.manifest, self.root)
        self.assertEqual(len(validated["targets"]), 3)
        provenance = pilot_runner.verify_pilot_extractions(self.root, validated["products"])
        self.assertEqual(set(provenance), {"pilot-top", "pilot-trousers", "pilot-skirt"})

    def test_missing_or_invalid_consent_rejected(self):
        for mutator in (
            lambda m: m["targets"][0].update(consent_confirmed=False),
            lambda m: m["targets"][1].update(adult_confirmed=False),
            lambda m: m["targets"][0].update(consent_record_id="  "),
            lambda m: m["targets"][2].update(consent_scope="public_showcase"),
            lambda m: m["targets"][0].update(retention_until="not-a-date"),
        ):
            bad = copy.deepcopy(self.manifest)
            mutator(bad)
            with self.assertRaises(ValueError):
                pilot_runner.validate_pilot_manifest(bad, self.root)

    def test_wrong_hashes_duplicate_target_or_path_escape_rejected(self):
        bad_hash = copy.deepcopy(self.manifest)
        bad_hash["targets"][0]["image_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(bad_hash, self.root)

        bad_prod_hash = copy.deepcopy(self.manifest)
        bad_prod_hash["products"][1]["image_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(bad_prod_hash, self.root)

        dup_target = copy.deepcopy(self.manifest)
        dup_target["targets"][1]["image"] = dup_target["targets"][0]["image"]
        dup_target["targets"][1]["image_sha256"] = dup_target["targets"][0]["image_sha256"]
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(dup_target, self.root)

        escape = copy.deepcopy(self.manifest)
        escape["targets"][0]["image"] = "../outside.jpg"
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(escape, self.root)

        # Tamper SAM2 mask and confirm verify_pilot_extractions rejects before GPU load.
        Image.new("L", (60, 80), 255).save(self.root / "runs/source-extraction-pilot-trousers-refined/mask.png")
        with self.assertRaises(ValueError):
            pilot_runner.verify_pilot_extractions(self.root, self.manifest["products"])

    def test_invalid_product_rules_rejected(self):
        for mutator in (
            lambda m: m["products"][0].update(garment_photo_type="flat-lay"),
            lambda m: m["products"][1].update(listing_ai_generated_label_observed=True),
            lambda m: m["products"][1].update(photo_origin="ai_generated"),
            lambda m: m["products"][2].update(product_url="https://example.com/item-p-1"),
            lambda m: m["products"][1].update(category="tops"),
        ):
            bad = copy.deepcopy(self.manifest)
            mutator(bad)
            with self.assertRaises(ValueError):
                pilot_runner.validate_pilot_manifest(bad, self.root)

    def test_invalid_or_unsupported_flows_rejected(self):
        for mutator in (
            lambda m: m["flows"][0].update(flow_type="dress"),
            lambda m: m["flows"][0].update(bottom_id="pilot-trousers"),
            lambda m: m["flows"][1].update(tuck_top=True),
            lambda m: m["flows"][1].update(bottom_id="pilot-skirt"),
            lambda m: m["flows"][2].update(bottom_id="pilot-trousers"),
            lambda m: m["flows"][2].pop("tuck_top"),
            lambda m: m["flows"].pop(1),
        ):
            bad = copy.deepcopy(self.manifest)
            mutator(bad)
            with self.assertRaises(ValueError):
                pilot_runner.validate_pilot_manifest(bad, self.root)

    def test_missing_parsing_label_is_recorded_as_parse_blocked_never_silently_skipped(self):
        # Target 2 lacks feet label 15; Target 3 lacks upper label 3.
        fake_pipeline = FakeFashnPipeline(
            target_labels_by_sha={(100, 210, 100): _no_feet_labels, (100, 100, 210): _no_upper_labels}
        )
        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            fashn_factory=lambda _r, _p: fake_pipeline,
            catvton_runner=_fake_catvton_success,
        )
        preflight = json.loads((run_dir / "parsing-preflight.json").read_text(encoding="utf-8"))
        self.assertTrue(preflight["pilot-target-1"]["passed_skirt_requirements"])
        self.assertFalse(preflight["pilot-target-2"]["passed_trousers_requirements"])
        self.assertEqual(preflight["pilot-target-2"]["missing_for_trousers_preservation"], [15])
        self.assertFalse(preflight["pilot-target-2"]["passed_skirt_requirements"])
        self.assertEqual(preflight["pilot-target-3"]["missing_for_trousers_preservation"], [3])
        self.assertEqual(preflight["pilot-target-3"]["missing_for_skirt_envelope"], [3])

        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "completed_with_parse_blocks")
        by_id = {c["id"]: c for c in summary["cases"]}
        self.assertEqual(by_id["pilot-target-2__top"]["status"], "completed")
        self.assertEqual(by_id["pilot-target-2__trousers"]["status"], "parse_blocked")
        self.assertEqual(by_id["pilot-target-2__skirt-tucked"]["status"], "parse_blocked")
        self.assertEqual(by_id["pilot-target-3__trousers"]["status"], "parse_blocked")
        self.assertEqual(by_id["pilot-target-3__skirt-tucked"]["status"], "parse_blocked")
        self.assertFalse((run_dir / "cases/pilot-target-2__trousers/result.png").exists())
        self.assertFalse((run_dir / "cases/pilot-target-2__trousers/02-bottom-raw.png").exists())
        self.assertFalse((run_dir / "cases/pilot-target-2__trousers/03-protected-outfit.png").exists())
        trousers_run = json.loads((run_dir / "cases/pilot-target-2__trousers/run.json").read_text(encoding="utf-8"))
        self.assertEqual(trousers_run["status"], "parse_blocked")
        self.assertFalse((run_dir / "cases/pilot-target-2__skirt-tucked/result.png").exists())
        self.assertFalse((run_dir / "cases/pilot-target-3__trousers/result.png").exists())
        self.assertFalse((run_dir / "cases/pilot-target-3__trousers/02-bottom-raw.png").exists())
        self.assertEqual(by_id["pilot-target-1__trousers"]["status"], "completed")
        self.assertEqual(by_id["pilot-target-1__skirt-tucked"]["status"], "completed")

        with (run_dir / "review-template.csv").open(encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 9)
        blocked_row = next(r for r in rows if r["id"] == "pilot-target-2__skirt-tucked")
        self.assertEqual(blocked_row["case_status"], "parse_blocked")
        self.assertEqual(blocked_row["reviewer"], "")
        self.assertEqual(blocked_row["garment_identity"], "")

    def test_missing_catvton_environment_fails_before_subprocess(self):
        with self.assertRaises(FileNotFoundError):
            pilot_runner.run_pilot(
                self.root,
                self.manifest_path,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
            )
        run_dir = next((self.root / "runs").glob("pilot-*"))
        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "failed")
        for case in summary["cases"]:
            if case["flow_type"] == "top_plus_skirt":
                self.assertEqual(case["status"], "failed")
                self.assertFalse((run_dir / "cases" / case["id"] / "result.png").exists())

    def test_catvton_subprocess_failure_never_creates_fake_result_or_success_status(self):
        cat_py = self.root / ".venv-catvton/Scripts/python.exe"
        cat_py.parent.mkdir(parents=True, exist_ok=True)
        cat_py.touch()

        def failing_subprocess(cmd, **_kwargs):
            raise subprocess.CalledProcessError(1, cmd)

        with self.assertRaises(subprocess.CalledProcessError):
            pilot_runner.run_pilot(
                self.root,
                self.manifest_path,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                subprocess_runner=failing_subprocess,
            )

        pilot_dirs = list((self.root / "runs").glob("pilot-*"))
        self.assertEqual(len(pilot_dirs), 1)
        run_dir = pilot_dirs[0]
        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "failed")
        for case in summary["cases"]:
            if case["flow_type"] == "top_plus_skirt":
                self.assertEqual(case["status"], "failed")
                self.assertFalse((run_dir / "cases" / case["id"] / "result.png").exists())
                self.assertFalse((run_dir / "cases" / case["id"] / "02-skirt-repaint.png").exists())

    def test_tampered_handoff_before_phase2_is_rejected(self):
        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            fashn_factory=lambda _r, _p: FakeFashnPipeline(),
            catvton_runner=lambda _r, _d: None,
        )
        # Re-open prepared handoff tampering check via verify_prepared inside run_catvton_lower.
        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        target_case = next(c for c in summary["cases"] if c["flow_type"] == "top_plus_skirt")
        target_case["status"] = "prepared"
        (run_dir / "pilot-summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (run_dir / "cases" / target_case["id"] / "cat-soft-mask.png").write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            pilot_runner.run_catvton_lower(self.root, run_dir, skirt_lower_fn=lambda _d: None)

    def test_full_end_to_end_pilot_strictly_writes_only_under_runs_pilot_with_9_and_12_cases(self):
        run_9 = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            include_untucked=False,
            fashn_factory=lambda _r, _p: FakeFashnPipeline(),
            catvton_runner=_fake_catvton_success,
        )
        run_12 = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            include_untucked=True,
            fashn_factory=lambda _r, _p: FakeFashnPipeline(),
            catvton_runner=_fake_catvton_success,
        )
        self.assertFalse((self.root / "runs/local-jobs").exists())
        self.assertEqual(list((self.root / "runs").glob("protected-outfit-*")), [])

        summary_9 = json.loads((run_9 / "pilot-summary.json").read_text(encoding="utf-8"))
        summary_12 = json.loads((run_12 / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary_9["status"], "completed")
        self.assertEqual(len(summary_9["cases"]), 9)
        self.assertEqual(summary_12["status"], "completed")
        self.assertEqual(len(summary_12["cases"]), 12)
        for case in summary_12["cases"]:
            self.assertEqual(case["status"], "completed")
            self.assertTrue((run_12 / case["result"]).is_file())
            self.assertTrue((run_12 / "cases" / case["id"] / "comparison.jpg").is_file())
        with (run_12 / "review-template.csv").open(encoding="utf-8") as stream:
            rows_12 = list(csv.DictReader(stream))
        self.assertEqual(len(rows_12), 12)
        top_row = next(r for r in rows_12 if r["flow_id"] == "top")
        self.assertEqual(top_row["waist_belt_transition"], "N/A")
        skirt_row = next(r for r in rows_12 if r["flow_id"] == "skirt-untucked")
        self.assertEqual(skirt_row["tuck_top"], "false")
        self.assertEqual(skirt_row["waist_belt_transition"], "")

    def test_duplicate_or_extra_core_flows_rejected(self):
        extra_core = copy.deepcopy(self.manifest)
        extra_core["flows"].append({"id": "top-extra", "flow_type": "top_only", "top_id": "pilot-top"})
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(extra_core, self.root)

        dup_sig = copy.deepcopy(self.manifest)
        dup_sig["flows"][1] = {"id": "top-dup", "flow_type": "top_only", "top_id": "pilot-top"}
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(dup_sig, self.root)

    def test_invalid_or_duplicate_optional_controls_rejected(self):
        for mutator in (
            lambda m: m["optional_controls"].__setitem__(0, {"id": "opt-top", "flow_type": "top_only", "top_id": "pilot-top"}),
            lambda m: m["optional_controls"].__setitem__(
                0, {"id": "opt-trousers", "flow_type": "top_plus_trousers", "top_id": "pilot-top", "bottom_id": "pilot-trousers"}
            ),
            lambda m: m["optional_controls"].__setitem__(
                0,
                {"id": "opt-tucked", "flow_type": "top_plus_skirt", "top_id": "pilot-top", "bottom_id": "pilot-skirt", "tuck_top": True},
            ),
            lambda m: m["optional_controls"].append(
                {
                    "id": "skirt-untucked-2",
                    "flow_type": "top_plus_skirt",
                    "top_id": "pilot-top",
                    "bottom_id": "pilot-skirt",
                    "tuck_top": False,
                }
            ),
        ):
            bad = copy.deepcopy(self.manifest)
            mutator(bad)
            with self.assertRaises(ValueError):
                pilot_runner.validate_pilot_manifest(bad, self.root)

    def test_expired_retention_until_and_compact_date_rejected(self):
        expired = copy.deepcopy(self.manifest)
        expired["targets"][0]["retention_until"] = (date.today() - timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(expired, self.root)

        compact = copy.deepcopy(self.manifest)
        compact["targets"][0]["retention_until"] = "20280101"
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(compact, self.root)

    def test_duplicate_body_group_across_targets_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["targets"][1]["body_group"] = bad["targets"][0]["body_group"]
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(bad, self.root)

    def test_missing_lower_garment_label_blocks_skirt_only(self):
        fake_pipeline = FakeFashnPipeline(target_labels_by_sha={(100, 210, 100): _no_lower_labels})
        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            fashn_factory=lambda _r, _p: fake_pipeline,
            catvton_runner=_fake_catvton_success,
        )
        preflight = json.loads((run_dir / "parsing-preflight.json").read_text(encoding="utf-8"))
        self.assertTrue(preflight["pilot-target-2"]["passed_trousers_requirements"])
        self.assertFalse(preflight["pilot-target-2"]["passed_skirt_requirements"])
        self.assertEqual(preflight["pilot-target-2"]["missing_for_skirt_envelope"], ["5|6|7|14"])

        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "completed_with_parse_blocks")
        by_id = {c["id"]: c for c in summary["cases"]}
        self.assertEqual(by_id["pilot-target-2__top"]["status"], "completed")
        self.assertEqual(by_id["pilot-target-2__trousers"]["status"], "completed")
        self.assertEqual(by_id["pilot-target-2__skirt-tucked"]["status"], "parse_blocked")
        self.assertFalse((run_dir / "cases/pilot-target-2__skirt-tucked/result.png").exists())
        self.assertFalse((run_dir / "cases/pilot-target-2__skirt-tucked/skirt-handoff.json").exists())

    def test_local_skirt_root_restored_after_error(self):
        original_root = local_skirt.ROOT
        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            fashn_factory=lambda _r, _p: FakeFashnPipeline(),
            catvton_runner=lambda _r, _d: None,
        )
        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        for case in summary["cases"]:
            if case["flow_type"] == "top_plus_skirt":
                case["status"] = "prepared"
        (run_dir / "pilot-summary.json").write_text(json.dumps(summary), encoding="utf-8")

        def failing_lower(_case_dir):
            self.assertEqual(local_skirt.ROOT, self.root.resolve())
            raise RuntimeError("Simulated CatVTON lower crash")

        try:
            with self.assertRaises(RuntimeError):
                pilot_runner.run_catvton_lower(self.root, run_dir, skirt_lower_fn=failing_lower)
            self.assertEqual(local_skirt.ROOT, original_root)
            updated = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
            first_skirt = next(c for c in updated["cases"] if c["flow_type"] == "top_plus_skirt")
            self.assertEqual(first_skirt["status"], "failed")
            self.assertFalse((run_dir / "cases" / first_skirt["id"] / "result.png").exists())
        finally:
            local_skirt.ROOT = original_root

    def test_wrong_python_environment_blocked_for_preflight_and_fashn_phase(self):
        # Controlled real CLI subprocess checks: without root/.venv, both commands fail before creating runs/pilot-*.
        for cmd_args in (
            ["preflight", "--root", str(self.root), "--manifest", str(self.manifest_path)],
            ["fashn-phase", "--root", str(self.root), "--run-dir", str(self.root / "runs/pilot-unused")],
        ):
            proc = subprocess.run(
                [sys.executable, "-u", str(APP_DIR / "pilot_runner.py"), *cmd_args],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("Isolated environment unavailable", proc.stderr)
        self.assertEqual(list((self.root / "runs").glob("pilot-*")), [])

        # Missing root/.venv also blocks run_pilot when fashn_factory is not injected.
        with self.assertRaises(FileNotFoundError):
            pilot_runner.run_pilot(self.root, self.manifest_path, fashn_factory=None)
        self.assertEqual(list((self.root / "runs").glob("pilot-*")), [])

        # Controlled venv redirection & loop-guard & subprocess command path checks.
        fashn_py = pilot_runner._venv_python(self.root, ".venv")
        fashn_py.parent.mkdir(parents=True, exist_ok=True)
        fashn_py.touch()

        redirect_calls = []

        def fake_redirect_runner(cmd, **kwargs):
            redirect_calls.append((cmd, kwargs))
            return SimpleNamespace(returncode=0)

        with self.assertRaises(SystemExit) as exit_info:
            pilot_runner._ensure_cli_venv(
                self.root,
                ".venv",
                ["preflight", "--root", str(self.root)],
                subprocess_runner=fake_redirect_runner,
            )
        self.assertEqual(exit_info.exception.code, 0)
        self.assertEqual(redirect_calls[0][0][0], str(fashn_py))
        self.assertEqual(redirect_calls[0][1]["env"][pilot_runner.REEXEC_ENV_VAR], ".venv")

        env = dict(os.environ)
        env[pilot_runner.REEXEC_ENV_VAR] = ".venv"
        loop_proc = subprocess.run(
            [sys.executable, "-u", str(APP_DIR / "pilot_runner.py"), "fashn-phase", "--root", str(self.root), "--run-dir", str(self.root / "runs/pilot-unused")],
            cwd=ROOT_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(loop_proc.returncode, 0)
        self.assertIn("failed to enter .venv interpreter", loop_proc.stderr.lower())

        # Direct Phase 1 call without fashn_factory rejects wrong interpreter before importing masked_outfit.
        direct_run_dir = self.root / "runs/pilot-direct-guard"
        direct_run_dir.mkdir(parents=True, exist_ok=True)
        with self.assertRaises(RuntimeError):
            pilot_runner.run_fashn_phase(self.root, direct_run_dir, fashn_factory=None)

        # run_pilot Phase 1 subprocess dispatch must invoke root/.venv Python (not sys.executable).
        seen_cmds = []

        def fake_phase_runner(cmd, **_kwargs):
            seen_cmds.append(cmd)
            if "fashn-phase" in cmd:
                run_dir_arg = Path(cmd[cmd.index("--run-dir") + 1])
                summary = json.loads((run_dir_arg / "pilot-summary.json").read_text(encoding="utf-8"))
                for case in summary["cases"]:
                    if case["flow_type"] == "top_plus_skirt":
                        case["status"] = "prepared"
                    else:
                        out = run_dir_arg / "cases" / case["id"] / "result.png"
                        out.parent.mkdir(parents=True, exist_ok=True)
                        Image.new("RGB", (60, 80), (10, 10, 10)).save(out)
                        case.update(status="completed", result=out.relative_to(run_dir_arg).as_posix(), output_sha256=sha256(out))
                pilot_runner._refresh_summary(self.root, run_dir_arg, summary)

        cat_py = pilot_runner._venv_python(self.root, ".venv-catvton")
        cat_py.parent.mkdir(parents=True, exist_ok=True)
        cat_py.touch()
        pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            fashn_factory=None,
            subprocess_runner=fake_phase_runner,
        )
        self.assertEqual(seen_cmds[0][0], str(fashn_py))
        self.assertIn("fashn-phase", seen_cmds[0])
        self.assertEqual(seen_cmds[1][0], str(cat_py))
        self.assertIn("catvton-lower", seen_cmds[1])

        self.assertEqual(
            pilot_runner._venv_python(self.root, ".venv", platform="linux"),
            self.root.resolve() / ".venv/bin/python",
        )

    def test_pipeline_error_in_compose_outfit_stays_failed_not_parse_blocked(self):
        broken_pipeline = RaisingStage2Pipeline(ValueError("Missing or mismatched garment instance mask"))
        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            fashn_factory=lambda _r, _p: broken_pipeline,
            catvton_runner=_fake_catvton_success,
        )
        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "failed")
        trousers_case = next(c for c in summary["cases"] if c["id"] == "pilot-target-1__trousers")
        self.assertEqual(trousers_case["status"], "failed")
        self.assertIn("garment instance mask", trousers_case["error"])
        case_dir = run_dir / "cases" / trousers_case["id"]
        self.assertFalse((case_dir / "result.png").exists())
        self.assertFalse((case_dir / "02-bottom-raw.png").exists())
        self.assertFalse((case_dir / "03-protected-outfit.png").exists())
        run_meta = json.loads((case_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(run_meta["status"], "failed")

        # Contrast: a parsing ValueError thrown inside compose_outfit transitions cleanly to parse_blocked.
        parsing_broken = RaisingStage2Pipeline(ValueError("No feet to preserve"))
        run_dir_2 = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            fashn_factory=lambda _r, _p: parsing_broken,
            catvton_runner=_fake_catvton_success,
        )
        summary_2 = json.loads((run_dir_2 / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary_2["status"], "completed_with_parse_blocks")
        trousers_case_2 = next(c for c in summary_2["cases"] if c["id"] == "pilot-target-1__trousers")
        self.assertEqual(trousers_case_2["status"], "parse_blocked")
        case_dir_2 = run_dir_2 / "cases" / trousers_case_2["id"]
        self.assertFalse((case_dir_2 / "result.png").exists())
        self.assertFalse((case_dir_2 / "02-bottom-raw.png").exists())
        self.assertTrue((case_dir_2 / "parsing-post-top.json").is_file())

    def test_invalid_post_top_parsing_array_records_parse_blocked_without_secondary_crash(self):
        # Target 1 passes preflight ((210,100,100) -> full labels), then post-top receives invalid labels ((211,100,100));
        # Target 3 fails preflight with invalid labels cleanly without crashing preflight.
        bad_parser_pipeline = FakeFashnPipeline(
            target_labels_by_sha={
                (211, 100, 100): _invalid_range_labels,
                (100, 100, 210): _invalid_range_labels,
            },
            top_tag_override={(210, 100, 100): (211, 100, 100)},
        )
        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            fashn_factory=lambda _r, _p: bad_parser_pipeline,
            catvton_runner=_fake_catvton_success,
        )
        preflight = json.loads((run_dir / "parsing-preflight.json").read_text(encoding="utf-8"))
        self.assertTrue(preflight["pilot-target-1"]["passed_skirt_requirements"])
        self.assertFalse(preflight["pilot-target-3"]["valid"])
        self.assertFalse(preflight["pilot-target-3"]["passed_trousers_requirements"])
        self.assertIn("audit_error", preflight["pilot-target-3"])

        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "completed_with_parse_blocks")
        by_id = {c["id"]: c for c in summary["cases"]}
        for blocked_id in ("pilot-target-1__trousers", "pilot-target-1__skirt-tucked"):
            case = by_id[blocked_id]
            self.assertEqual(case["status"], "parse_blocked")
            case_dir = run_dir / "cases" / blocked_id
            self.assertFalse((case_dir / "result.png").exists())
            self.assertFalse((case_dir / "02-bottom-raw.png").exists())
            self.assertFalse((case_dir / "03-protected-outfit.png").exists())
            audit = json.loads((case_dir / "parsing-post-top.json").read_text(encoding="utf-8"))
            self.assertFalse(audit["valid"])
            self.assertIn("audit_error", audit)


if __name__ == "__main__":
    unittest.main()
