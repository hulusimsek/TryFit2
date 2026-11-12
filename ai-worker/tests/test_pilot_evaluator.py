import csv
import json
import tempfile
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
ROOT_DIR = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(APP_DIR))

from experiment import METRICS
from pilot_runner import PILOT_EXTRA_METRICS
import pilot_evaluator


def _create_pilot_summary(cases, *, include_untucked=False, is_synthetic=False):
    summary = {
        "schema_version": 1,
        "status": "completed",
        "scope": "pilot validation",
        "include_untucked": include_untucked,
        "cases": cases,
    }
    if is_synthetic:
        summary["pilot_mode"] = "synthetic_technical_rehearsal"
        summary["manifest_kind"] = "synthetic_technical_pilot"
    return summary


def _create_manifest(targets, flows, optional_controls=None):
    return {
        "schema_version": 1,
        "targets": [{"id": tid, "body_group": "medium"} for tid in targets],
        "flows": flows,
        "optional_controls": optional_controls or [],
    }


def _make_review_row(case_id, reviewer, *, score="4", extra_score="4", flow_type="top_only", crit="no", untarg="no", notes=""):
    row = {
        "id": case_id,
        "reviewer": reviewer,
        "critical_failure": crit,
        "untargeted_changes": untarg,
        "notes": notes,
    }
    for m in METRICS:
        row[m] = score
    for m in PILOT_EXTRA_METRICS:
        row[m] = "N/A" if flow_type == "top_only" else extra_score
    return row


def _write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


class PilotEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        self.targets = ["target-1", "target-2", "target-3"]
        self.flows = [
            {"id": "top", "flow_type": "top_only"},
            {"id": "trousers", "flow_type": "top_plus_trousers"},
            {"id": "skirt-tucked", "flow_type": "top_plus_skirt"},
        ]
        self.optional_controls = [
            {"id": "skirt-untucked", "flow_type": "top_plus_skirt"},
        ]

        # 9 default cases
        self.cases = []
        for tid in self.targets:
            for fl in self.flows:
                self.cases.append({
                    "id": f"{tid}__{fl['id']}",
                    "target_id": tid,
                    "flow_id": fl["id"],
                    "flow_type": fl["flow_type"],
                    "status": "completed",
                })

        self.manifest = _create_manifest(self.targets, self.flows, self.optional_controls)
        self.summary = _create_pilot_summary(self.cases)

        (self.root / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        (self.root / "pilot-summary.json").write_text(json.dumps(self.summary), encoding="utf-8")

    def test_two_reviewers_full_pass(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"], score="4", extra_score="4") for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"], score="3", extra_score="3") for c in self.cases]

        r1_csv = self.root / "r1.csv"
        r2_csv = self.root / "r2.csv"
        _write_csv(r1_csv, r1_rows)
        _write_csv(r2_csv, r2_rows)

        report = pilot_evaluator.evaluate_pilot_run(self.root, [r1_csv, r2_csv])

        self.assertEqual(report["general_quality_gate"], "not_established")
        self.assertIn(">=80% genel kalite kapısı kurulmamıştır", report["general_quality_gate_rationale"])
        self.assertIs(report["generalization_evidence"], False)
        self.assertEqual(report["suite_summary"]["expected_cases_count"], 9)
        self.assertEqual(report["suite_summary"]["completed_cases_count"], 9)
        self.assertEqual(report["suite_summary"]["provisional_passed_count"], 9)
        self.assertEqual(report["suite_summary"]["provisional_failed_count"], 0)
        self.assertEqual(report["suite_summary"]["total_score_discrepancies_count"], 0)
        self.assertEqual(report["pilot_acceptance"]["status"], "provisionally_acceptable")

        for case in report["cases"]:
            self.assertEqual(case["provisional_automatic_decision"], "passed")
            self.assertEqual(case["evaluator_1"]["scores"]["garment_identity"], 4)
            self.assertEqual(case["evaluator_2"]["scores"]["garment_identity"], 3)
            self.assertEqual(case["provisional_min_scores"]["garment_identity"], 3)
            self.assertFalse(case["has_score_discrepancies"])
            self.assertFalse(case["veto_triggered"])
            self.assertFalse(case["human_adjudication_required"])

    def test_score_discrepancy_detected(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"], score="4") for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"], score="4") for c in self.cases]

        # Case 0: Reviewer B gives 2 on 'cut' (diff: 4 - 2 = 2)
        r2_rows[0]["cut"] = "2"

        r1_csv = self.root / "r1.csv"
        r2_csv = self.root / "r2.csv"
        _write_csv(r1_csv, r1_rows)
        _write_csv(r2_csv, r2_rows)

        report = pilot_evaluator.evaluate_pilot_run(self.root, [r1_csv, r2_csv])

        c0 = report["cases"][0]
        self.assertTrue(c0["has_score_discrepancies"])
        self.assertEqual(len(c0["score_discrepancies"]), 1)
        self.assertEqual(c0["score_discrepancies"][0]["metric"], "cut")
        self.assertEqual(c0["score_discrepancies"][0]["absolute_difference"], 2)
        self.assertEqual(c0["provisional_min_scores"]["cut"], 2)
        self.assertEqual(c0["provisional_automatic_decision"], "failed")
        self.assertTrue(c0["human_adjudication_required"])

        self.assertEqual(report["suite_summary"]["total_score_discrepancies_count"], 1)
        self.assertEqual(report["pilot_acceptance"]["status"], "pending_human_adjudication")

    def test_veto_by_single_reviewer_critical_failure(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"], score="4") for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"], score="4") for c in self.cases]

        # Case 1: Reviewer B flags critical_failure
        r2_rows[1]["critical_failure"] = "yes"

        r1_csv = self.root / "r1.csv"
        r2_csv = self.root / "r2.csv"
        _write_csv(r1_csv, r1_rows)
        _write_csv(r2_csv, r2_rows)

        report = pilot_evaluator.evaluate_pilot_run(self.root, [r1_csv, r2_csv])

        c1 = report["cases"][1]
        self.assertTrue(c1["veto_triggered"])
        self.assertIn("Reviewer B: critical_failure=yes", c1["veto_reasons"])
        self.assertEqual(c1["provisional_automatic_decision"], "failed")

    def test_veto_by_single_reviewer_untargeted_changes(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"], score="4") for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"], score="4") for c in self.cases]

        # Case 2: Reviewer A flags untargeted_changes
        r1_rows[2]["untargeted_changes"] = "yes"

        combined_csv = self.root / "review.csv"
        _write_csv(combined_csv, r1_rows + r2_rows)

        report = pilot_evaluator.evaluate_pilot_run(self.root, combined_csv)

        c2 = report["cases"][2]
        self.assertTrue(c2["veto_triggered"])
        self.assertIn("Reviewer A: untargeted_changes=yes", c2["veto_reasons"])
        self.assertEqual(c2["provisional_automatic_decision"], "failed")

    def test_top_only_allows_na_for_extra_metrics(self):
        case = self.cases[0]
        self.assertEqual(case["flow_type"], "top_only")

        r1_row = _make_review_row(case["id"], "Reviewer A", flow_type="top_only", score="4")
        r2_row = _make_review_row(case["id"], "Reviewer B", flow_type="top_only", score="4")

        eval_case = pilot_evaluator.evaluate_case(case, r1_row, r2_row, "Reviewer A", "Reviewer B")
        self.assertEqual(eval_case["provisional_automatic_decision"], "passed")
        self.assertEqual(eval_case["evaluator_1"]["scores"]["waist_belt_transition"], "N/A")
        self.assertNotIn("waist_belt_transition", eval_case["provisional_min_scores"])

    def test_two_stage_rejects_na_for_extra_metrics(self):
        case = self.cases[1]
        self.assertEqual(case["flow_type"], "top_plus_trousers")

        r1_row = _make_review_row(case["id"], "Reviewer A", flow_type="top_plus_trousers", score="4")
        # Illegally set waist_belt_transition to N/A on a two-stage flow
        r1_row["waist_belt_transition"] = "N/A"
        r2_row = _make_review_row(case["id"], "Reviewer B", flow_type="top_plus_trousers", score="4")

        eval_case = pilot_evaluator.evaluate_case(case, r1_row, r2_row, "Reviewer A", "Reviewer B")
        self.assertEqual(eval_case["provisional_automatic_decision"], "pending_review")
        self.assertTrue(any("two-stage flow requires numeric" in err for err in eval_case.get("validation_errors", [])))

    def test_dynamic_case_count_derivation(self):
        # 12 cases with include_untucked=True
        cases_12 = []
        for tid in self.targets:
            for fl in self.flows + self.optional_controls:
                cases_12.append({
                    "id": f"{tid}__{fl['id']}",
                    "target_id": tid,
                    "flow_id": fl["id"],
                    "flow_type": fl["flow_type"],
                    "status": "completed",
                })
        summary_12 = _create_pilot_summary(cases_12, include_untucked=True)
        (self.root / "pilot-summary.json").write_text(json.dumps(summary_12), encoding="utf-8")

        expected = pilot_evaluator.derive_expected_cases(self.root)
        self.assertEqual(len(expected), 12)
        self.assertEqual({c["id"] for c in expected}, {c["id"] for c in cases_12})

    def test_unexecuted_manifest_case_reported_as_not_generated(self):
        # Remove 1 case from summary to simulate incomplete generation
        incomplete_cases = self.cases[:-1]
        summary_incomplete = _create_pilot_summary(incomplete_cases)
        (self.root / "pilot-summary.json").write_text(json.dumps(summary_incomplete), encoding="utf-8")

        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"], score="4") for c in incomplete_cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"], score="4") for c in incomplete_cases]

        report = pilot_evaluator.evaluate_pilot_run(self.root, [_write_csv(self.root / "r1.csv", r1_rows), _write_csv(self.root / "r2.csv", r2_rows)])

        self.assertEqual(report["suite_summary"]["expected_cases_count"], 9)
        self.assertEqual(report["suite_summary"]["completed_cases_count"], 8)
        self.assertEqual(report["suite_summary"]["not_generated_count"], 1)
        self.assertEqual(report["pilot_acceptance"]["status"], "pending")

        missing_case = next(c for c in report["cases"] if c["id"] == self.cases[-1]["id"])
        self.assertEqual(missing_case["execution_status"], "not_generated")
        self.assertEqual(missing_case["provisional_automatic_decision"], "not_generated")

    def test_unexpected_case_id_rejected(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"]) for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"]) for c in self.cases]

        # Add an unknown ID
        r1_rows.append(_make_review_row("unknown-target__unknown-flow", "Reviewer A"))

        _write_csv(self.root / "r1.csv", r1_rows)
        _write_csv(self.root / "r2.csv", r2_rows)

        with self.assertRaises(ValueError) as ctx:
            pilot_evaluator.evaluate_pilot_run(self.root, [self.root / "r1.csv", self.root / "r2.csv"])
        self.assertIn("unknown case", str(ctx.exception).lower())

    def test_single_reviewer_rejected(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"]) for c in self.cases]
        _write_csv(self.root / "r1.csv", r1_rows)

        with self.assertRaises(ValueError) as ctx:
            pilot_evaluator.evaluate_pilot_run(self.root, [self.root / "r1.csv"])
        self.assertIn("exactly two independent reviewers", str(ctx.exception).lower())

    def test_duplicate_review_by_same_reviewer_rejected(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"]) for c in self.cases]
        r1_rows.append(_make_review_row(self.cases[0]["id"], "Reviewer A", flow_type=self.cases[0]["flow_type"]))

        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"]) for c in self.cases]

        _write_csv(self.root / "r1.csv", r1_rows)
        _write_csv(self.root / "r2.csv", r2_rows)

        with self.assertRaises(ValueError) as ctx:
            pilot_evaluator.evaluate_pilot_run(self.root, [self.root / "r1.csv", self.root / "r2.csv"])
        self.assertIn("duplicate review", str(ctx.exception).lower())

    def test_identical_reviewer_names_rejected(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"]) for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "reviewer a", flow_type=c["flow_type"]) for c in self.cases]

        _write_csv(self.root / "r1.csv", r1_rows)
        _write_csv(self.root / "r2.csv", r2_rows)

        with self.assertRaises(ValueError) as ctx:
            pilot_evaluator.evaluate_pilot_run(self.root, [self.root / "r1.csv", self.root / "r2.csv"])
        self.assertIn("distinct individuals", str(ctx.exception).lower())

    def test_mismatched_target_or_flow_id_rejected(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"]) for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"]) for c in self.cases]

        # Add target_id and flow_id columns
        for row in r1_rows:
            target_id, flow_id = row["id"].split("__")
            row["target_id"] = target_id
            row["flow_id"] = flow_id
        for row in r2_rows:
            target_id, flow_id = row["id"].split("__")
            row["target_id"] = target_id
            row["flow_id"] = flow_id

        # Mismatch target_id on case 0
        r1_rows[0]["target_id"] = "wrong-target"

        _write_csv(self.root / "r1.csv", r1_rows)
        _write_csv(self.root / "r2.csv", r2_rows)

        with self.assertRaises(ValueError) as ctx:
            pilot_evaluator.evaluate_pilot_run(self.root, [self.root / "r1.csv", self.root / "r2.csv"])
        self.assertIn("mismatched target_id", str(ctx.exception).lower())

    def test_parse_blocked_and_failed_cases_never_pass_even_with_perfect_scores(self):
        # Case 0 is parse_blocked, Case 1 is failed
        self.cases[0]["status"] = "parse_blocked"
        self.cases[1]["status"] = "failed"
        self.summary["cases"] = self.cases
        (self.root / "pilot-summary.json").write_text(json.dumps(self.summary), encoding="utf-8")

        # Reviewers generously gave 4/4 to all cases
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"], score="4", extra_score="4") for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"], score="4", extra_score="4") for c in self.cases]

        _write_csv(self.root / "r1.csv", r1_rows)
        _write_csv(self.root / "r2.csv", r2_rows)

        report = pilot_evaluator.evaluate_pilot_run(self.root, [self.root / "r1.csv", self.root / "r2.csv"])

        c0 = report["cases"][0]
        c1 = report["cases"][1]
        self.assertEqual(c0["execution_status"], "parse_blocked")
        self.assertEqual(c0["provisional_automatic_decision"], "parse_blocked")
        self.assertEqual(c1["execution_status"], "failed")
        self.assertEqual(c1["provisional_automatic_decision"], "failed")

        self.assertEqual(report["suite_summary"]["completed_cases_count"], 7)
        self.assertEqual(report["suite_summary"]["provisional_passed_count"], 7)
        self.assertEqual(report["suite_summary"]["not_generated_count"], 1)
        self.assertEqual(report["suite_summary"]["provisional_failed_count"], 1)
        self.assertEqual(report["pilot_acceptance"]["status"], "pending")

    def test_cli_main_execution(self):
        r1_rows = [_make_review_row(c["id"], "Reviewer A", flow_type=c["flow_type"]) for c in self.cases]
        r2_rows = [_make_review_row(c["id"], "Reviewer B", flow_type=c["flow_type"]) for c in self.cases]

        _write_csv(self.root / "r1.csv", r1_rows)
        _write_csv(self.root / "r2.csv", r2_rows)

        out_file = self.root / "custom-evaluation.json"
        code = pilot_evaluator.main([
            "--run-dir", str(self.root),
            "--reviews", str(self.root / "r1.csv"), str(self.root / "r2.csv"),
            "--out", str(out_file),
        ])
        self.assertEqual(code, 0)
        self.assertTrue(out_file.is_file())
        saved_data = json.loads(out_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_data["schema_version"], 1)
        self.assertEqual(saved_data["general_quality_gate"], "not_established")


if __name__ == "__main__":
    unittest.main()
