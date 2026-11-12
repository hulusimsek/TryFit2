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


def _build_synthetic_fixture_repo(root: Path):
    (root / "runs").mkdir(parents=True, exist_ok=True)
    avatar_dir = root / "data/avatar-profiles"
    baseline_dir = root / "data/first-outfit"
    bench_dir = root / "data/benchmark-10"
    manifest_dir = root / "data/pilot-synthetic"
    for directory in (avatar_dir, baseline_dir, bench_dir, manifest_dir):
        directory.mkdir(parents=True, exist_ok=True)

    baseline_path = baseline_dir / "avatar-baseline.png"
    target_specs = [
        ("slender", "slender", avatar_dir / "slender.png", (210, 100, 100), "evaluation/annotations/avatar-profile-generation.json"),
        ("medium", "medium", baseline_path, (100, 210, 100), "docs/avatar-baseline.md"),
        ("fuller", "fuller", avatar_dir / "fuller.png", (100, 100, 210), "evaluation/annotations/avatar-profile-generation.json"),
    ]
    targets = []
    for tid, group, img_path, color, gen_record in target_specs:
        Image.new("RGB", (60, 80), color).save(img_path)
        targets.append(
            {
                "id": tid,
                "body_group": group,
                "target_origin": "synthetic_visual_preset",
                "derived_from_base_image": "data/first-outfit/avatar-baseline.png",
                "generation_record": gen_record,
                "image": img_path.relative_to(root).as_posix(),
                "image_sha256": sha256(img_path),
                "measured": False,
                "pose_notes": "Synthetic frontal standing full-body studio pose",
                "footwear_notes": "Bare feet flat on neutral studio floor",
                "current_clothing_notes": "Plain fitted light-grey top and grey leggings",
                "lighting_background_notes": "Uniform pale grey seamless studio background",
            }
        )

    product_specs = [
        ("tshirt", "Tişört", "top", "tops", bench_dir / "tshirt.jpg", (220, 40, 40)),
        ("skirt", "Etek", "skirt", "bottoms", bench_dir / "skirt.jpg", (20, 20, 20)),
    ]
    products = []
    for pid, label, role, category, img_path, color in product_specs:
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
                "label": label,
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
        "manifest_kind": "synthetic_technical_pilot",
        "purpose": "Fixture isolated 2-flow synthetic technical rehearsal",
        "generalization_evidence": False,
        "same_base_identity": True,
        "effective_subject_diversity": 1,
        "derived_from_baseline": "data/first-outfit/avatar-baseline.png",
        "included_flows": ["top_only", "top_plus_skirt"],
        "excluded_flows": ["top_plus_trousers"],
        "targets": targets,
        "products": products,
        "flows": [
            {"id": "top", "flow_type": "top_only", "top_id": "tshirt"},
            {"id": "skirt-tucked", "flow_type": "top_plus_skirt", "top_id": "tshirt", "bottom_id": "skirt", "tuck_top": True},
            {"id": "skirt-untucked", "flow_type": "top_plus_skirt", "top_id": "tshirt", "bottom_id": "skirt", "tuck_top": False},
        ],
    }
    manifest_path = manifest_dir / "synthetic-2flow-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest, manifest_path


def _fake_catvton_outcome(case_dir: Path):
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


def _fake_catvton_success(root: Path, run_dir: Path):
    pilot_runner.run_catvton_lower(root, run_dir, skirt_lower_fn=_fake_catvton_outcome)


def _fake_catvton_synthetic_success(root: Path, run_dir: Path):
    pilot_runner.run_catvton_lower(
        root,
        run_dir,
        skirt_lower_fn=_fake_catvton_outcome,
        synthetic_tech=True,
    )


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


class SyntheticTechPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.real_manifest, self.real_manifest_path = _build_fixture_repo(self.root)
        self.manifest, self.manifest_path = _build_synthetic_fixture_repo(self.root)

    def test_repo_synthetic_manifest_contract_and_live_extractions(self):
        repo_manifest_path = ROOT_DIR / "evaluation/manifests/pilot-synthetic-2flow.json"
        repo_manifest = json.loads(repo_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(repo_manifest["manifest_kind"], "synthetic_technical_pilot")
        self.assertIs(repo_manifest["generalization_evidence"], False)
        self.assertIs(repo_manifest["same_base_identity"], True)
        self.assertEqual(repo_manifest["effective_subject_diversity"], 1)
        self.assertEqual(repo_manifest["included_flows"], ["top_only", "top_plus_skirt"])
        self.assertEqual(repo_manifest["excluded_flows"], ["top_plus_trousers"])

        hashes = set()
        for target in repo_manifest["targets"]:
            for forbidden in pilot_runner.REAL_CONSENT_FORBIDDEN_FIELDS:
                self.assertNotIn(forbidden, target)
            self.assertEqual(target["target_origin"], "synthetic_visual_preset")
            self.assertEqual(target["derived_from_base_image"], repo_manifest["derived_from_baseline"])
            hashes.add(target["image_sha256"])
        self.assertEqual(len(hashes), 3)

        required_assets = [ROOT_DIR / t["image"] for t in repo_manifest["targets"]] + [
            ROOT_DIR / p["image"] for p in repo_manifest["products"]
        ]
        required_extractions = [
            ROOT_DIR / f"runs/source-extraction-{p['id']}-refined/extraction.json"
            for p in repo_manifest["products"]
        ]
        if all(path.is_file() for path in required_assets + required_extractions):
            validated = pilot_runner.validate_synthetic_pilot_manifest(repo_manifest, ROOT_DIR)
            provenance = pilot_runner.verify_pilot_extractions(ROOT_DIR, validated["products"])
            self.assertEqual(set(provenance), {"tshirt", "skirt"})
            with self.assertRaises(ValueError):
                pilot_runner.validate_pilot_manifest(repo_manifest, ROOT_DIR)

    def test_bidirectional_isolation_and_synthetic_manifest_guards(self):
        validated = pilot_runner.validate_synthetic_pilot_manifest(self.manifest, self.root)
        self.assertEqual(len(validated["targets"]), 3)
        self.assertEqual(len(validated["products"]), 2)

        # Real validator must reject synthetic manifest even if caller invokes real mode.
        with self.assertRaises(ValueError):
            pilot_runner.validate_pilot_manifest(self.manifest, self.root)

        # Synthetic validator must reject real manifests and the unfilled real template.
        with self.assertRaises(ValueError):
            pilot_runner.validate_synthetic_pilot_manifest(self.real_manifest, self.root)
        template_manifest = json.loads(
            (ROOT_DIR / "evaluation/manifests/pilot-3x3.template.json").read_text(encoding="utf-8")
        )
        with self.assertRaises(ValueError):
            pilot_runner.validate_synthetic_pilot_manifest(template_manifest, ROOT_DIR)

        # Reject any forged real-consent fields on synthetic targets.
        for field, value in (
            ("adult_confirmed", True),
            ("consent_confirmed", True),
            ("consent_record_id", "FAKE-01"),
            ("consent_scope", pilot_runner.ALLOWED_CONSENT_SCOPE),
            ("retention_until", "2099-01-01"),
        ):
            forged = copy.deepcopy(self.manifest)
            forged["targets"][0][field] = value
            with self.assertRaises(ValueError):
                pilot_runner.validate_synthetic_pilot_manifest(forged, self.root)

        # Reject attempts to misrepresent synthetic run as generalization or multi-identity evidence.
        for mutator in (
            lambda m: m.__setitem__("generalization_evidence", True),
            lambda m: m.__setitem__("same_base_identity", False),
            lambda m: m.__setitem__("effective_subject_diversity", 3),
            lambda m: m.__setitem__("excluded_flows", []),
            lambda m: m.__setitem__("included_flows", ["top_only", "top_plus_trousers", "top_plus_skirt"]),
            lambda m: m.__setitem__("optional_controls", [{"id": "extra", "flow_type": "top_plus_skirt", "top_id": "tshirt", "bottom_id": "skirt", "tuck_top": False}]),
        ):
            bad = copy.deepcopy(self.manifest)
            mutator(bad)
            with self.assertRaises(ValueError):
                pilot_runner.validate_synthetic_pilot_manifest(bad, self.root)

        # Duplicate SHA-256 across two synthetic avatars must fail.
        dup_img = copy.deepcopy(self.manifest)
        dup_path = self.root / dup_img["targets"][0]["image"]
        same_bytes_path = self.root / dup_img["targets"][2]["image"]
        dup_path.write_bytes(same_bytes_path.read_bytes())
        dup_img["targets"][0]["image_sha256"] = sha256(dup_path)
        with self.assertRaises(ValueError):
            pilot_runner.validate_synthetic_pilot_manifest(dup_img, self.root)

        # Reject trousers flow/product, wide-trousers reference, or missing untucked flow.
        trousers_img = self.root / "data/benchmark-10/wide-trousers.jpg"
        Image.new("RGB", (60, 80), (40, 40, 220)).save(trousers_img)
        trousers_prod = copy.deepcopy(self.manifest)
        trousers_prod["products"].append(
            {
                "id": "wide-trousers",
                "label": "Pantolon",
                "flow_role": "trousers",
                "category": "bottoms",
                "garment_photo_type": "model",
                "image": trousers_img.relative_to(self.root).as_posix(),
                "image_sha256": sha256(trousers_img),
                "product_url": "https://www.trendyol.com/fixture/wide-trousers-p-999",
                "source_image_url": "https://cdn.example.invalid/wide-trousers.jpg",
                "photo_origin": "real_model_photo",
                "listing_ai_generated_label_observed": False,
                "source_notes": "Synthetic guard test trousers",
            }
        )
        trousers_prod["flows"].append(
            {"id": "trousers", "flow_type": "top_plus_trousers", "top_id": "tshirt", "bottom_id": "wide-trousers"}
        )
        with self.assertRaises(ValueError):
            pilot_runner.validate_synthetic_pilot_manifest(trousers_prod, self.root)

        missing_untucked = copy.deepcopy(self.manifest)
        missing_untucked["flows"].pop()
        with self.assertRaises(ValueError):
            pilot_runner.validate_synthetic_pilot_manifest(missing_untucked, self.root)

        # Reject --include-untucked under synthetic mode.
        with self.assertRaises(ValueError):
            pilot_runner.run_pilot(
                self.root,
                self.manifest_path,
                include_untucked=True,
                synthetic_tech=True,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                catvton_runner=_fake_catvton_synthetic_success,
            )

    def test_end_to_end_9_case_synthetic_mock_run_verifies_every_avatar_and_flow(self):
        fake_fashn = FakeFashnPipeline()
        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            synthetic_tech=True,
            fashn_factory=lambda _r, _p: fake_fashn,
            catvton_runner=_fake_catvton_synthetic_success,
        )
        self.assertTrue(run_dir.name.startswith("pilot-"))

        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["pilot_mode"], "synthetic_technical_rehearsal")
        self.assertEqual(summary["manifest_kind"], "synthetic_technical_pilot")
        self.assertIs(summary["generalization_evidence"], False)
        self.assertIs(summary["same_base_identity"], True)
        self.assertEqual(summary["effective_subject_diversity"], 1)
        self.assertIs(summary["distinct_target_sha256"], True)
        self.assertEqual(summary["excluded_flows"], ["top_plus_trousers"])
        self.assertEqual(summary["included_flows"], ["top_only", "top_plus_skirt"])
        self.assertEqual(len(set(summary["target_sha256s"].values())), 3)
        self.assertEqual(summary["counts"], {"completed": 9})

        cases_by_pair = {(c["target_id"], c["flow_id"]): c for c in summary["cases"]}
        expected_pairs = [
            (avatar, flow_id)
            for avatar in ("slender", "medium", "fuller")
            for flow_id in ("top", "skirt-tucked", "skirt-untucked")
        ]
        self.assertEqual(set(cases_by_pair), set(expected_pairs))
        for avatar, flow_id in expected_pairs:
            case = cases_by_pair[(avatar, flow_id)]
            self.assertEqual(case["status"], "completed")
            self.assertNotEqual(case["flow_type"], "top_plus_trousers")
            case_dir = run_dir / "cases" / case["id"]
            self.assertTrue((case_dir / "result.png").is_file(), f"Missing result.png for {case['id']}")
            self.assertTrue((case_dir / "comparison.jpg").is_file(), f"Missing comparison.jpg for {case['id']}")
            selection = json.loads((case_dir / "selection.json").read_text(encoding="utf-8"))
            self.assertEqual(selection["pilot_mode"], "synthetic_technical_rehearsal")
            self.assertIs(selection["generalization_evidence"], False)
            if flow_id == "skirt-tucked":
                self.assertIs(case["tuck_top"], True)
                self.assertIs(selection["tuck_top"], True)
            elif flow_id == "skirt-untucked":
                self.assertIs(case["tuck_top"], False)
                self.assertIs(selection["tuck_top"], False)
            else:
                self.assertIsNone(case["tuck_top"])

        with (run_dir / "review-template.csv").open("r", newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 9)
        csv_pairs = {(row["target_id"], row["flow_id"]): row for row in rows}
        self.assertEqual(set(csv_pairs), set(expected_pairs))
        for pair in expected_pairs:
            row = csv_pairs[pair]
            self.assertEqual(row["case_status"], "completed")
            self.assertEqual(row["pilot_mode"], "synthetic_technical_rehearsal")
            self.assertEqual(row["generalization_evidence"], "false")

    def test_phase_security_validates_manifest_and_blocks_cross_mode_execution(self):
        # Subprocess orchestrator must forward --synthetic-tech to both phase subprocesses.
        recorded_cmds = []

        def fake_subprocess(cmd, check=True, cwd=None):
            recorded_cmds.append(list(cmd))
            if "fashn-phase" in cmd:
                pilot_runner.run_fashn_phase(
                    self.root,
                    cmd[cmd.index("--run-dir") + 1],
                    fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                    synthetic_tech=("--synthetic-tech" in cmd),
                )
            elif "catvton-lower" in cmd:
                pilot_runner.run_catvton_lower(
                    self.root,
                    cmd[cmd.index("--run-dir") + 1],
                    skirt_lower_fn=_fake_catvton_outcome,
                    synthetic_tech=("--synthetic-tech" in cmd),
                )

        with patch.object(pilot_runner, "_require_venv_python", return_value=Path(sys.executable)):
            run_dir = pilot_runner.run_pilot(
                self.root,
                self.manifest_path,
                synthetic_tech=True,
                run_phase1_in_subprocess=True,
                subprocess_runner=fake_subprocess,
            )
        self.assertEqual(len(recorded_cmds), 2)
        self.assertIn("fashn-phase", recorded_cmds[0])
        self.assertIn("--synthetic-tech", recorded_cmds[0])
        self.assertIn("catvton-lower", recorded_cmds[1])
        self.assertIn("--synthetic-tech", recorded_cmds[1])

        # Prepare a Phase 1 synthetic run_dir without executing Phase 2 yet.
        captured_dirs = []

        def halt_phase2(_root, d):
            captured_dirs.append(d)
            raise RuntimeError("halt before phase 2")

        with patch.object(pilot_runner, "_require_venv_python", return_value=Path(sys.executable)):
            with self.assertRaises(RuntimeError):
                pilot_runner.run_pilot(
                    self.root,
                    self.manifest_path,
                    synthetic_tech=True,
                    fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                    catvton_runner=halt_phase2,
                )
        self.assertEqual(len(captured_dirs), 1)
        prepared_run_dir = captured_dirs[0]

        # Cross-mode execution must be refused by both phases.
        with self.assertRaises(ValueError):
            pilot_runner.run_fashn_phase(
                self.root,
                prepared_run_dir,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                synthetic_tech=False,
            )
        with self.assertRaises(ValueError):
            pilot_runner.run_catvton_lower(
                self.root,
                prepared_run_dir,
                skirt_lower_fn=_fake_catvton_outcome,
                synthetic_tech=False,
            )

        # Real run_dir must be refused under synthetic_tech=True.
        with self.assertRaises(ValueError):
            pilot_runner.run_fashn_phase(
                self.root,
                run_dir,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                synthetic_tech=False,
            )
        real_run_dir = pilot_runner.run_pilot(
            self.root,
            self.real_manifest_path,
            fashn_factory=lambda _r, _p: FakeFashnPipeline(),
            catvton_runner=_fake_catvton_success,
        )
        with self.assertRaises(ValueError):
            pilot_runner.run_fashn_phase(
                self.root,
                real_run_dir,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                synthetic_tech=True,
            )
        with self.assertRaises(ValueError):
            pilot_runner.run_catvton_lower(
                self.root,
                real_run_dir,
                skirt_lower_fn=_fake_catvton_outcome,
                synthetic_tech=True,
            )

        # Tampering manifest.json inside run_dir (even with manifest_kind/pilot_mode matching) must be caught
        # because both phases re-run the full synthetic validator on manifest.json.
        tampered_manifest_path = prepared_run_dir / "manifest.json"
        tampered = json.loads(tampered_manifest_path.read_text(encoding="utf-8"))
        tampered["targets"][0]["adult_confirmed"] = True
        tampered_manifest_path.write_text(json.dumps(tampered), encoding="utf-8")
        with self.assertRaises(ValueError):
            pilot_runner.run_fashn_phase(
                self.root,
                prepared_run_dir,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                synthetic_tech=True,
            )
        with self.assertRaises(ValueError):
            pilot_runner.run_catvton_lower(
                self.root,
                prepared_run_dir,
                skirt_lower_fn=_fake_catvton_outcome,
                synthetic_tech=True,
            )

        # Tampering pilot-summary.json inside run_dir (even with valid manifest.json) must also be caught.
        tampered_summary_path = run_dir / "pilot-summary.json"
        tampered_summary = json.loads(tampered_summary_path.read_text(encoding="utf-8"))
        tampered_summary.pop("pilot_mode")
        tampered_summary_path.write_text(json.dumps(tampered_summary), encoding="utf-8")
        with self.assertRaises(ValueError):
            pilot_runner.run_fashn_phase(
                self.root,
                run_dir,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                synthetic_tech=True,
            )
        with self.assertRaises(ValueError):
            pilot_runner.run_catvton_lower(
                self.root,
                run_dir,
                skirt_lower_fn=_fake_catvton_outcome,
                synthetic_tech=True,
            )

        # Wrong Python interpreter under --synthetic-tech CLI commands must fail cleanly.
        for args in (
            ["preflight", "--root", str(self.root), "--manifest", str(self.manifest_path), "--synthetic-tech"],
            ["fashn-phase", "--root", str(self.root), "--run-dir", str(run_dir), "--synthetic-tech"],
            ["catvton-lower", "--root", str(self.root), "--run-dir", str(run_dir), "--synthetic-tech"],
        ):
            self.assertEqual(pilot_runner.main(args), 1)

    def test_synthetic_parsing_block_leaves_no_result_png(self):
        # Target "fuller" ((100,100,210)) shifts post-top to (101,100,210) missing feet -> parse_blocked on skirts.
        partial_parser = FakeFashnPipeline(
            target_labels_by_sha={(101, 100, 210): _no_feet_labels},
            top_tag_override={(100, 100, 210): (101, 100, 210)},
        )
        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            synthetic_tech=True,
            fashn_factory=lambda _r, _p: partial_parser,
            catvton_runner=_fake_catvton_synthetic_success,
        )
        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "completed_with_parse_blocks")
        self.assertEqual(summary["counts"], {"completed": 7, "parse_blocked": 2})

        by_id = {c["id"]: c for c in summary["cases"]}
        self.assertEqual(by_id["fuller__top"]["status"], "completed")
        for blocked in ("fuller__skirt-tucked", "fuller__skirt-untucked"):
            self.assertEqual(by_id[blocked]["status"], "parse_blocked")
            case_dir = run_dir / "cases" / blocked
            self.assertFalse((case_dir / "result.png").exists())
            self.assertFalse((case_dir / "02-skirt-repaint.png").exists())

    def test_single_case_slender_top_runs_only_selected_case_and_skips_catvton(self):
        fake_fashn = FakeFashnPipeline()
        catvton_calls = []

        def forbid_catvton(root, run_dir):
            catvton_calls.append((root, run_dir))
            raise AssertionError("CatVTON must never be called in single-case mode.")

        run_dir = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            synthetic_tech=True,
            case_id="slender__top",
            fashn_factory=lambda _r, _p: fake_fashn,
            catvton_runner=forbid_catvton,
        )
        self.assertEqual(catvton_calls, [])
        self.assertEqual(len(fake_fashn.calls), 1)
        self.assertEqual(fake_fashn.calls[0]["category"], "tops")
        self.assertEqual(fake_fashn.hp_model.calls, 1)

        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["counts"], {"completed": 1})
        self.assertIs(summary["single_case_mode"], True)
        self.assertEqual(summary["execution_mode"], "single_case_fashn_only")
        self.assertEqual(summary["selected_case_id"], "slender__top")
        self.assertEqual(summary["selected_target_id"], "slender")
        self.assertEqual(summary["selected_flow_id"], "top")
        self.assertEqual(summary["selected_product_id"], "tshirt")
        self.assertIs(summary["fashn_only"], True)
        self.assertIs(summary["catvton_executed"], False)
        self.assertIs(summary["catvton_skipped"], True)
        self.assertIs(summary["settings"]["catvton"]["skipped"], True)
        self.assertEqual(summary["pilot_mode"], "synthetic_technical_rehearsal")
        self.assertIs(summary["generalization_evidence"], False)

        # Preflight and case directories must only contain slender and slender__top.
        preflight = json.loads((run_dir / "parsing-preflight.json").read_text(encoding="utf-8"))
        self.assertEqual(set(preflight.keys()), {"slender"})
        self.assertEqual([p.name for p in (run_dir / "cases").iterdir()], ["slender__top"])
        self.assertEqual(len(summary["cases"]), 1)
        case = summary["cases"][0]
        self.assertEqual(case["id"], "slender__top")
        self.assertEqual(case["target_id"], "slender")
        self.assertEqual(case["flow_id"], "top")
        self.assertEqual(case["flow_type"], "top_only")
        self.assertEqual(case["top_id"], "tshirt")
        self.assertIsNone(case["bottom_id"])
        self.assertIs(case["single_case_mode"], True)
        self.assertIs(case["catvton_skipped"], True)

        case_dir = run_dir / "cases" / "slender__top"
        self.assertTrue((case_dir / "result.png").is_file())
        self.assertTrue((case_dir / "comparison.jpg").is_file())
        selection = json.loads((case_dir / "selection.json").read_text(encoding="utf-8"))
        self.assertEqual(selection["target"]["id"], "slender")
        self.assertEqual([item["id"] for item in selection["items"]], ["tshirt"])
        self.assertEqual(selection["flow_type"], "top_only")
        self.assertIs(selection["single_case_mode"], True)
        self.assertEqual(selection["execution_mode"], "single_case_fashn_only")
        self.assertIs(selection["catvton_skipped"], True)

        with (run_dir / "review-template.csv").open("r", newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "slender__top")
        self.assertEqual(rows[0]["case_status"], "completed")
        self.assertEqual(rows[0]["pilot_mode"], "synthetic_technical_rehearsal")
        self.assertEqual(rows[0]["generalization_evidence"], "false")
        self.assertIn("catvton_skipped=true", rows[0]["notes"])

        # Direct or subprocess CatVTON invocation on a single-case run_dir must be rejected.
        with self.assertRaises(ValueError):
            pilot_runner.run_catvton_lower(
                self.root,
                run_dir,
                skirt_lower_fn=_fake_catvton_outcome,
                synthetic_tech=True,
            )

        # Subprocess orchestrator must invoke fashn-phase only and never invoke catvton-lower.
        sub_cmds = []

        def fake_sub(cmd, check=True, cwd=None):
            sub_cmds.append(list(cmd))
            if "fashn-phase" in cmd:
                pilot_runner.run_fashn_phase(
                    self.root,
                    cmd[cmd.index("--run-dir") + 1],
                    fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                    synthetic_tech=("--synthetic-tech" in cmd),
                )

        with patch.object(pilot_runner, "_require_venv_python", return_value=Path(sys.executable)):
            pilot_runner.run_pilot(
                self.root,
                self.manifest_path,
                synthetic_tech=True,
                case_id="slender__top",
                run_phase1_in_subprocess=True,
                subprocess_runner=fake_sub,
            )
        self.assertEqual(len(sub_cmds), 1)
        self.assertIn("fashn-phase", sub_cmds[0])
        self.assertIn("--synthetic-tech", sub_cmds[0])

    def test_single_case_invalid_or_ambiguous_selectors_rejected(self):
        before_runs = set((self.root / "runs").glob("pilot-*"))
        for bad_case in ("", "   ", "slender", "nonexistent__top", "slender__trousers", "medium__unknown"):
            with self.assertRaises(ValueError):
                pilot_runner.run_pilot(
                    self.root,
                    self.manifest_path,
                    synthetic_tech=True,
                    case_id=bad_case,
                    fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                    catvton_runner=_fake_catvton_synthetic_success,
                )
        # --case without --synthetic-tech must fail for both top_only and top_plus_skirt and leave real pilot untouched.
        for real_case in ("pilot-target-1__top", "pilot-target-1__skirt-tucked"):
            with self.assertRaises(ValueError):
                pilot_runner.run_pilot(
                    self.root,
                    self.real_manifest_path,
                    synthetic_tech=False,
                    case_id=real_case,
                    fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                    catvton_runner=_fake_catvton_success,
                )
        # Disallowed flow_type in expanded cases (e.g. top_plus_trousers) must be rejected by selector.
        with self.assertRaises(ValueError):
            pilot_runner._select_single_case(
                [{"id": "slender__trousers", "flow_type": "top_plus_trousers"}],
                "slender__trousers",
            )
        # Duplicate case IDs in expanded list must raise ambiguity error.
        with self.assertRaises(ValueError):
            pilot_runner._select_single_case(
                [
                    {"id": "dup__top", "flow_type": "top_only"},
                    {"id": "dup__top", "flow_type": "top_only"},
                ],
                "dup__top",
            )
        # Invalid selectors must not leave stray pilot-* run directories behind.
        self.assertEqual(set((self.root / "runs").glob("pilot-*")), before_runs)
        # CLI invalid --case exits cleanly with code 1.
        self.assertEqual(
            pilot_runner.main(
                ["run", "--root", str(self.root), "--manifest", str(self.manifest_path), "--synthetic-tech", "--case", "invalid__case"]
            ),
            1,
        )

    def test_single_case_slender_skirt_tucked_and_untucked_run_both_phases_for_selected_only(self):
        for case_selector, expected_flow_id, expected_tuck in (
            ("slender__skirt-tucked", "skirt-tucked", True),
            ("slender__skirt-untucked", "skirt-untucked", False),
        ):
            fake_fashn = FakeFashnPipeline()
            catvton_case_dirs = []

            def spy_skirt_lower(case_dir):
                catvton_case_dirs.append(case_dir.name)
                _fake_catvton_outcome(case_dir)

            run_dir = pilot_runner.run_pilot(
                self.root,
                self.manifest_path,
                synthetic_tech=True,
                case_id=case_selector,
                fashn_factory=lambda _r, _p: fake_fashn,
                catvton_runner=lambda r, d: pilot_runner.run_catvton_lower(
                    r, d, skirt_lower_fn=spy_skirt_lower, synthetic_tech=True
                ),
            )

            # Exactly 1 FASHN call and 1 CatVTON call for the single selected case only; other 7+ cases untouched.
            self.assertEqual(len(fake_fashn.calls), 1)
            self.assertEqual(fake_fashn.calls[0]["category"], "tops")
            self.assertEqual(catvton_case_dirs, [case_selector])

            preflight = json.loads((run_dir / "parsing-preflight.json").read_text(encoding="utf-8"))
            self.assertEqual(set(preflight.keys()), {"slender"})
            self.assertEqual([p.name for p in (run_dir / "cases").iterdir()], [case_selector])

            summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["counts"], {"completed": 1})
            self.assertIs(summary["single_case_mode"], True)
            self.assertEqual(summary["execution_mode"], "single_case_fashn_and_catvton")
            self.assertEqual(summary["selected_case_id"], case_selector)
            self.assertEqual(summary["selected_target_id"], "slender")
            self.assertEqual(summary["selected_flow_id"], expected_flow_id)
            self.assertEqual(summary["selected_product_id"], "tshirt")
            self.assertEqual(summary["selected_bottom_id"], "skirt")
            self.assertIs(summary["tuck_top"], expected_tuck)
            self.assertIs(summary["fashn_only"], False)
            self.assertIs(summary["fashn_executed"], True)
            self.assertIs(summary["catvton_executed"], True)
            self.assertIs(summary["catvton_skipped"], False)
            self.assertEqual(summary["pilot_mode"], "synthetic_technical_rehearsal")
            self.assertIs(summary["generalization_evidence"], False)
            self.assertEqual(summary["settings"]["catvton"], {"steps": 50, "guidance": 2.5, "seed": 42})

            self.assertEqual(len(summary["cases"]), 1)
            case = summary["cases"][0]
            self.assertEqual(case["id"], case_selector)
            self.assertEqual(case["target_id"], "slender")
            self.assertEqual(case["flow_id"], expected_flow_id)
            self.assertEqual(case["flow_type"], "top_plus_skirt")
            self.assertIs(case["tuck_top"], expected_tuck)
            self.assertIs(case["single_case_mode"], True)
            self.assertEqual(case["execution_mode"], "single_case_fashn_and_catvton")
            self.assertIs(case["fashn_executed"], True)
            self.assertIs(case["catvton_executed"], True)
            self.assertIs(case["catvton_skipped"], False)

            case_dir = run_dir / "cases" / case_selector
            for expected_file in (
                "01-top.png",
                "skirt-handoff.json",
                "02-skirt-raw.png",
                "02-skirt-repaint.png",
                "catvton-outcome.json",
                "result.png",
                "comparison.jpg",
            ):
                self.assertTrue((case_dir / expected_file).is_file(), f"Missing {expected_file}")

            handoff = json.loads((case_dir / "skirt-handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(bool(handoff["annotation"]["tuck_top"]), expected_tuck)

            selection = json.loads((case_dir / "selection.json").read_text(encoding="utf-8"))
            self.assertEqual(selection["target"]["id"], "slender")
            self.assertEqual([item["id"] for item in selection["items"]], ["tshirt", "skirt"])
            self.assertEqual(selection["flow_type"], "top_plus_skirt")
            self.assertIs(selection["tuck_top"], expected_tuck)
            self.assertIs(selection["single_case_mode"], True)
            self.assertEqual(selection["execution_mode"], "single_case_fashn_and_catvton")
            self.assertEqual(selection["selected_case_id"], case_selector)
            self.assertIs(selection["fashn_executed"], True)
            self.assertIs(selection["catvton_executed"], True)
            self.assertIs(selection["catvton_skipped"], False)
            self.assertIs(selection["generalization_evidence"], False)

            with (run_dir / "review-template.csv").open("r", newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["id"], case_selector)
            self.assertEqual(row["case_status"], "completed")
            self.assertEqual(row["tuck_top"], str(expected_tuck).lower())
            self.assertEqual(row["pilot_mode"], "synthetic_technical_rehearsal")
            self.assertEqual(row["generalization_evidence"], "false")
            for token in (
                "single_case_mode=true",
                "execution_mode=single_case_fashn_and_catvton",
                f"selected_case_id={case_selector}",
                "fashn_executed=true",
                "catvton_executed=true",
                "catvton_skipped=false",
                "generalization_evidence=false",
            ):
                self.assertIn(token, row["notes"])

    def test_single_case_skirt_subprocess_venvs_and_mode_guards(self):
        recorded_cmds = []
        fashn_venv = self.root / ".venv/Scripts/python.exe"
        catvton_venv = self.root / ".venv-catvton/Scripts/python.exe"

        def fake_venv_resolver(root, venv_name):
            return fashn_venv if venv_name == ".venv" else catvton_venv

        def fake_subprocess(cmd, check=True, cwd=None):
            recorded_cmds.append(list(cmd))
            if "fashn-phase" in cmd:
                pilot_runner.run_fashn_phase(
                    self.root,
                    cmd[cmd.index("--run-dir") + 1],
                    fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                    synthetic_tech=("--synthetic-tech" in cmd),
                )
            elif "catvton-lower" in cmd:
                pilot_runner.run_catvton_lower(
                    self.root,
                    cmd[cmd.index("--run-dir") + 1],
                    skirt_lower_fn=_fake_catvton_outcome,
                    synthetic_tech=("--synthetic-tech" in cmd),
                )

        with patch.object(pilot_runner, "_require_venv_python", side_effect=fake_venv_resolver):
            run_dir = pilot_runner.run_pilot(
                self.root,
                self.manifest_path,
                synthetic_tech=True,
                case_id="slender__skirt-tucked",
                run_phase1_in_subprocess=True,
                subprocess_runner=fake_subprocess,
            )

        self.assertEqual(len(recorded_cmds), 2)
        self.assertEqual(Path(recorded_cmds[0][0]), fashn_venv)
        self.assertIn("fashn-phase", recorded_cmds[0])
        self.assertIn("--synthetic-tech", recorded_cmds[0])
        self.assertEqual(Path(recorded_cmds[1][0]), catvton_venv)
        self.assertIn("catvton-lower", recorded_cmds[1])
        self.assertIn("--synthetic-tech", recorded_cmds[1])

        # Cross-mode calls must still be refused for single-case skirt run_dir.
        with self.assertRaises(ValueError):
            pilot_runner.run_fashn_phase(
                self.root,
                run_dir,
                fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                synthetic_tech=False,
            )
        with self.assertRaises(ValueError):
            pilot_runner.run_catvton_lower(
                self.root,
                run_dir,
                skirt_lower_fn=_fake_catvton_outcome,
                synthetic_tech=False,
            )

        # Tampering execution_mode or catvton_skipped in pilot-summary.json must be rejected.
        summary_path = run_dir / "pilot-summary.json"
        orig_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for bad_patch in (
            {"execution_mode": "single_case_fashn_only"},
            {"catvton_skipped": True},
        ):
            tampered = dict(orig_summary, **bad_patch)
            summary_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                pilot_runner.run_fashn_phase(
                    self.root,
                    run_dir,
                    fashn_factory=lambda _r, _p: FakeFashnPipeline(),
                    synthetic_tech=True,
                )
            with self.assertRaises(ValueError):
                pilot_runner.run_catvton_lower(
                    self.root,
                    run_dir,
                    skirt_lower_fn=_fake_catvton_outcome,
                    synthetic_tech=True,
                )

    def test_single_case_skirt_skips_catvton_when_fashn_fails_or_parse_blocked(self):
        # Case 1: FASHN fails with exception -> CatVTON must NOT run.
        catvton_calls = []

        class FailingFashnPipeline(FakeFashnPipeline):
            def __call__(self, **kwargs):
                raise RuntimeError("FASHN failure")

        run_dir_fail = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            synthetic_tech=True,
            case_id="slender__skirt-tucked",
            fashn_factory=lambda _r, _p: FailingFashnPipeline(),
            catvton_runner=lambda r, d: catvton_calls.append((r, d)),
        )
        self.assertEqual(catvton_calls, [])
        fail_summary = json.loads((run_dir_fail / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(fail_summary["status"], "failed")
        self.assertIs(fail_summary["fashn_executed"], False)
        self.assertIs(fail_summary["catvton_executed"], False)
        self.assertEqual(fail_summary["cases"][0]["status"], "failed")
        self.assertFalse((run_dir_fail / "cases" / "slender__skirt-tucked" / "result.png").exists())

        # Case 2: Post-top parsing blocks skirt preparation -> CatVTON must NOT run.
        partial_parser = FakeFashnPipeline(
            target_labels_by_sha={(211, 100, 100): _no_feet_labels},
            top_tag_override={(210, 100, 100): (211, 100, 100)},
        )
        run_dir_blocked = pilot_runner.run_pilot(
            self.root,
            self.manifest_path,
            synthetic_tech=True,
            case_id="slender__skirt-untucked",
            fashn_factory=lambda _r, _p: partial_parser,
            catvton_runner=lambda r, d: catvton_calls.append((r, d)),
        )
        self.assertEqual(catvton_calls, [])
        blocked_summary = json.loads((run_dir_blocked / "pilot-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(blocked_summary["status"], "completed_with_parse_blocks")
        self.assertIs(blocked_summary["fashn_executed"], True)
        self.assertIs(blocked_summary["catvton_executed"], False)
        self.assertEqual(blocked_summary["cases"][0]["status"], "parse_blocked")
        self.assertFalse((run_dir_blocked / "cases" / "slender__skirt-untucked" / "result.png").exists())


if __name__ == "__main__":
    unittest.main()
