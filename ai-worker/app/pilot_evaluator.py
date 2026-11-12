"""Independent evaluation and consensus summary tool for 3x3 real-person pilot runs.

Consolidates scores from two independent reviewers, tracks metric discrepancies,
enforces veto rules (critical_failure, untargeted_changes), and records provisional
automatic decisions while strictly separating them from human adjudication and signoff.

General quality gate is always declared 'not_established'; limited pilot evidence
never proves general product quality or 80%+ generalization.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from experiment import METRICS, write_json
from pilot_runner import PILOT_EXTRA_METRICS

SCORE_VALUES = {"0", "1", "2", "3", "4"}
BOOLEAN_CHOICES = {"yes", "no"}
NA_VALUES = {"n/a", "na", ""}

GENERAL_QUALITY_GATE_RATIONALE = (
    "Sınırlı 3 katılımcılı pilot genel ürün kalitesini veya beden uyumunu kanıtlamaz; "
    ">=80% genel kalite kapısı kurulmamıştır."
)


def _normalize_choice(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_na(value: Any) -> bool:
    return _normalize_choice(value) in NA_VALUES


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Review CSV file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return [{k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()} for row in reader]


def load_review_records(review_paths: list[Path] | Path) -> dict[str, dict[str, dict[str, str]]]:
    """Load reviews from one or multiple CSV files, grouped by reviewer then case id.

    Returns: {reviewer_name: {case_id: row_dict}}
    Raises: ValueError on duplicates, missing reviewer, or unexpected reviewer counts.
    """
    if isinstance(review_paths, (str, Path)):
        paths = [Path(review_paths)]
    else:
        paths = [Path(p) for p in review_paths]

    reviews_by_evaluator: dict[str, dict[str, dict[str, str]]] = {}

    for path in paths:
        rows = _load_csv_rows(path)
        for row in rows:
            case_id = (row.get("id") or "").strip()
            if not case_id:
                raise ValueError(f"Review row in {path.name} is missing 'id'.")
            reviewer = (row.get("reviewer") or "").strip()
            if not reviewer:
                raise ValueError(f"Review row for case {case_id!r} in {path.name} has empty 'reviewer'.")

            evaluator_reviews = reviews_by_evaluator.setdefault(reviewer, {})
            if case_id in evaluator_reviews:
                raise ValueError(
                    f"Duplicate review for case {case_id!r} by reviewer {reviewer!r} (observed in {path.name})."
                )
            evaluator_reviews[case_id] = row

    reviewer_names = sorted(reviews_by_evaluator.keys())
    if len(reviewer_names) != 2:
        raise ValueError(
            f"Pilot evaluation requires exactly two independent reviewers; found {len(reviewer_names)}: {reviewer_names}"
        )
    if reviewer_names[0].strip().lower() == reviewer_names[1].strip().lower():
        raise ValueError(
            f"Reviewers must be distinct individuals; received identical reviewer identities: {reviewer_names}"
        )

    return reviews_by_evaluator


def derive_expected_cases(run_dir: Path) -> list[dict[str, Any]]:
    """Derive expected cases dynamically from manifest.json and pilot-summary.json.

    Never hardcodes 9 or 12. If single_case_mode is active, derives the single case.
    """
    run_dir = Path(run_dir)
    summary_path = run_dir / "pilot-summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"pilot-summary.json not found in {run_dir}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    manifest_path = run_dir / "manifest.json"
    manifest: dict[str, Any] | None = None
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    summary_cases = summary.get("cases", [])
    summary_by_id = {c["id"]: c for c in summary_cases}

    is_single_case = bool(summary.get("single_case_mode"))
    include_untucked = bool(summary.get("include_untucked"))

    expected: list[dict[str, Any]] = []

    if is_single_case:
        for sc in summary_cases:
            expected.append({
                "id": sc["id"],
                "target_id": sc.get("target_id", ""),
                "flow_id": sc.get("flow_id", ""),
                "flow_type": sc.get("flow_type", "top_only"),
                "tuck_top": sc.get("tuck_top"),
                "summary_status": sc.get("status", "pending"),
            })
        return expected

    if manifest and "targets" in manifest and "flows" in manifest:
        flows = list(manifest.get("flows", []))
        if include_untucked:
            flows.extend(manifest.get("optional_controls", []))
        for target in manifest.get("targets", []):
            for flow in flows:
                cid = f"{target['id']}__{flow['id']}"
                summary_entry = summary_by_id.get(cid, {})
                expected.append({
                    "id": cid,
                    "target_id": target["id"],
                    "flow_id": flow["id"],
                    "flow_type": flow.get("flow_type", "top_only"),
                    "tuck_top": flow.get("tuck_top"),
                    "summary_status": summary_entry.get("status", "not_generated"),
                })
        return expected

    # Fallback to summary cases directly if manifest is absent
    for sc in summary_cases:
        expected.append({
            "id": sc["id"],
            "target_id": sc.get("target_id", ""),
            "flow_id": sc.get("flow_id", ""),
            "flow_type": sc.get("flow_type", "top_only"),
            "tuck_top": sc.get("tuck_top"),
            "summary_status": sc.get("status", "pending"),
        })
    return expected


def evaluate_case(
    case_meta: dict[str, Any],
    r1: dict[str, str] | None,
    r2: dict[str, str] | None,
    evaluator_1_name: str,
    evaluator_2_name: str,
) -> dict[str, Any]:
    """Evaluate a single case given reviews from two independent evaluators."""
    case_id = case_meta["id"]
    flow_type = case_meta.get("flow_type", "top_only")
    summary_status = case_meta.get("summary_status") or case_meta.get("status") or "not_generated"

    is_top_only = (flow_type == "top_only")
    applicable_metrics = list(METRICS)
    if not is_top_only:
        applicable_metrics.extend(PILOT_EXTRA_METRICS)

    result: dict[str, Any] = {
        "id": case_id,
        "target_id": case_meta.get("target_id", ""),
        "flow_id": case_meta.get("flow_id", ""),
        "flow_type": flow_type,
        "tuck_top": case_meta.get("tuck_top"),
        "execution_status": summary_status,
        "evaluator_1": None,
        "evaluator_2": None,
        "has_score_discrepancies": False,
        "score_discrepancies": [],
        "veto_triggered": False,
        "veto_reasons": [],
        "provisional_min_scores": {},
        "provisional_automatic_decision": "pending_review",
        "human_adjudication_required": False,
        "final_human_signoff": {
            "status": "pending_human_signoff",
            "decision": None,
            "adjudicated_by": None,
            "notes": None,
        },
    }

    if r1 is None or r2 is None:
        if summary_status != "completed":
            result["provisional_automatic_decision"] = "not_generated" if summary_status == "not_generated" else summary_status
        else:
            result["provisional_automatic_decision"] = "pending_review"
        return result

    # Validate evaluator 1
    r1_scores: dict[str, Any] = {}
    r2_scores: dict[str, Any] = {}
    validation_errors: list[str] = []

    for m in METRICS:
        v1 = r1.get(m, "").strip()
        v2 = r2.get(m, "").strip()
        if v1 not in SCORE_VALUES:
            validation_errors.append(f"{evaluator_1_name}: invalid {m}={v1!r}")
        if v2 not in SCORE_VALUES:
            validation_errors.append(f"{evaluator_2_name}: invalid {m}={v2!r}")
        r1_scores[m] = int(v1) if v1 in SCORE_VALUES else v1
        r2_scores[m] = int(v2) if v2 in SCORE_VALUES else v2

    for m in PILOT_EXTRA_METRICS:
        v1 = r1.get(m, "").strip()
        v2 = r2.get(m, "").strip()
        if is_top_only:
            if not _is_na(v1):
                validation_errors.append(f"{evaluator_1_name}: {m} must be 'N/A' for top_only, got {v1!r}")
            if not _is_na(v2):
                validation_errors.append(f"{evaluator_2_name}: {m} must be 'N/A' for top_only, got {v2!r}")
            r1_scores[m] = "N/A"
            r2_scores[m] = "N/A"
        else:
            if v1 not in SCORE_VALUES:
                validation_errors.append(f"{evaluator_1_name}: two-stage flow requires numeric {m}, got {v1!r}")
            if v2 not in SCORE_VALUES:
                validation_errors.append(f"{evaluator_2_name}: two-stage flow requires numeric {m}, got {v2!r}")
            r1_scores[m] = int(v1) if v1 in SCORE_VALUES else v1
            r2_scores[m] = int(v2) if v2 in SCORE_VALUES else v2

    r1_crit = _normalize_choice(r1.get("critical_failure"))
    r2_crit = _normalize_choice(r2.get("critical_failure"))
    r1_untarg = _normalize_choice(r1.get("untargeted_changes"))
    r2_untarg = _normalize_choice(r2.get("untargeted_changes"))

    if r1_crit not in BOOLEAN_CHOICES:
        validation_errors.append(f"{evaluator_1_name}: critical_failure must be yes/no, got {r1.get('critical_failure')!r}")
    if r2_crit not in BOOLEAN_CHOICES:
        validation_errors.append(f"{evaluator_2_name}: critical_failure must be yes/no, got {r2.get('critical_failure')!r}")
    if r1_untarg not in BOOLEAN_CHOICES:
        validation_errors.append(f"{evaluator_1_name}: untargeted_changes must be yes/no, got {r1.get('untargeted_changes')!r}")
    if r2_untarg not in BOOLEAN_CHOICES:
        validation_errors.append(f"{evaluator_2_name}: untargeted_changes must be yes/no, got {r2.get('untargeted_changes')!r}")

    result["evaluator_1"] = {
        "reviewer": evaluator_1_name,
        "scores": r1_scores,
        "critical_failure": r1_crit,
        "untargeted_changes": r1_untarg,
        "notes": r1.get("notes", "").strip(),
    }
    result["evaluator_2"] = {
        "reviewer": evaluator_2_name,
        "scores": r2_scores,
        "critical_failure": r2_crit,
        "untargeted_changes": r2_untarg,
        "notes": r2.get("notes", "").strip(),
    }

    if summary_status != "completed":
        result["provisional_automatic_decision"] = "not_generated" if summary_status == "not_generated" else summary_status
        return result

    if validation_errors:
        result["validation_errors"] = validation_errors
        result["provisional_automatic_decision"] = "pending_review"
        return result

    # Discrepancy checks (|s1 - s2| >= 2)
    discrepancies: list[dict[str, Any]] = []
    min_scores: dict[str, int] = {}
    for m in applicable_metrics:
        s1 = r1_scores[m]
        s2 = r2_scores[m]
        diff = abs(s1 - s2)
        if diff >= 2:
            discrepancies.append({
                "metric": m,
                f"{evaluator_1_name}_score": s1,
                f"{evaluator_2_name}_score": s2,
                "absolute_difference": diff,
            })
        min_scores[m] = min(s1, s2)

    result["has_score_discrepancies"] = (len(discrepancies) > 0)
    result["score_discrepancies"] = discrepancies
    result["provisional_min_scores"] = min_scores

    # Veto rules
    veto_reasons: list[str] = []
    if r1_crit == "yes":
        veto_reasons.append(f"{evaluator_1_name}: critical_failure=yes")
    if r2_crit == "yes":
        veto_reasons.append(f"{evaluator_2_name}: critical_failure=yes")
    if r1_untarg == "yes":
        veto_reasons.append(f"{evaluator_1_name}: untargeted_changes=yes")
    if r2_untarg == "yes":
        veto_reasons.append(f"{evaluator_2_name}: untargeted_changes=yes")

    result["veto_triggered"] = (len(veto_reasons) > 0)
    result["veto_reasons"] = veto_reasons

    # Provisional automatic decision (conservative min score >= 3, no veto)
    min_applicable = min(min_scores.values()) if min_scores else 0
    if result["veto_triggered"]:
        provisional = "failed"
    elif min_applicable >= 3:
        provisional = "passed"
    else:
        provisional = "failed"

    result["provisional_automatic_decision"] = provisional

    # Human adjudication is required if there are score discrepancies (diff >= 2)
    # or conflicting boolean veto indicators
    conflicting_vetos = (r1_crit != r2_crit) or (r1_untarg != r2_untarg)
    result["human_adjudication_required"] = bool(result["has_score_discrepancies"] or conflicting_vetos)

    return result


def evaluate_pilot_run(
    run_dir: Path | str,
    review_paths: list[Path] | Path | None = None,
) -> dict[str, Any]:
    """Execute complete independent evaluation on a pilot run directory."""
    run_dir = Path(run_dir).resolve()
    summary_path = run_dir / "pilot-summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"pilot-summary.json not found in {run_dir}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    if review_paths is None:
        candidates = [run_dir / "review.csv", run_dir / "review-completed.csv"]
        found = [p for p in candidates if p.is_file()]
        if not found:
            raise FileNotFoundError(f"No review CSV found in {run_dir}; specify --reviews.")
        review_paths = found

    reviews_by_evaluator = load_review_records(review_paths)
    evaluator_names = sorted(reviews_by_evaluator.keys())
    eval1_name, eval2_name = evaluator_names[0], evaluator_names[1]

    expected_cases = derive_expected_cases(run_dir)
    expected_cases_by_id = {c["id"]: c for c in expected_cases}
    expected_ids = set(expected_cases_by_id.keys())

    # Reject unexpected case IDs or mismatched target/flow in reviews
    for name, rmap in reviews_by_evaluator.items():
        for cid, row in rmap.items():
            if cid not in expected_ids:
                raise ValueError(
                    f"Reviewer {name!r} submitted score for unknown case {cid!r}; not in expected pilot suite."
                )
            cmeta = expected_cases_by_id[cid]
            row_target = (row.get("target_id") or "").strip()
            if row_target and row_target != cmeta.get("target_id", ""):
                raise ValueError(
                    f"Reviewer {name!r} submitted row for {cid!r} with mismatched target_id: "
                    f"expected {cmeta.get('target_id')!r}, got {row_target!r}."
                )
            row_flow = (row.get("flow_id") or "").strip()
            if row_flow and row_flow != cmeta.get("flow_id", ""):
                raise ValueError(
                    f"Reviewer {name!r} submitted row for {cid!r} with mismatched flow_id: "
                    f"expected {cmeta.get('flow_id')!r}, got {row_flow!r}."
                )

    cases_evaluations: list[dict[str, Any]] = []
    provisional_passed = 0
    provisional_failed = 0
    pending_review = 0
    not_generated = 0
    total_discrepancies = 0

    for case_meta in expected_cases:
        cid = case_meta["id"]
        r1 = reviews_by_evaluator[eval1_name].get(cid)
        r2 = reviews_by_evaluator[eval2_name].get(cid)
        evaluated = evaluate_case(case_meta, r1, r2, eval1_name, eval2_name)
        cases_evaluations.append(evaluated)

        dec = evaluated["provisional_automatic_decision"]
        if dec == "passed":
            provisional_passed += 1
        elif dec == "failed":
            provisional_failed += 1
        elif dec == "pending_review":
            pending_review += 1
        else:
            not_generated += 1

        total_discrepancies += len(evaluated.get("score_discrepancies", []))

    expected_count = len(expected_cases)
    completed_count = sum(1 for c in expected_cases if c.get("summary_status") == "completed")

    # Determine pilot acceptance provisional status
    if not_generated > 0 or pending_review > 0:
        acceptance_status = "pending"
    elif total_discrepancies > 0:
        acceptance_status = "pending_human_adjudication"
    elif provisional_passed == expected_count and expected_count > 0:
        acceptance_status = "provisionally_acceptable"
    else:
        acceptance_status = "failed"

    is_synthetic = (
        summary.get("pilot_mode") == "synthetic_technical_rehearsal"
        or summary.get("manifest_kind") == "synthetic_technical_pilot"
    )

    evaluation_report: dict[str, Any] = {
        "schema_version": 1,
        "pilot_kind": "synthetic_technical_rehearsal" if is_synthetic else "real_3x3_pilot",
        "evaluation_type": "dual_independent_review_summary",
        "general_quality_gate": "not_established",
        "general_quality_gate_rationale": GENERAL_QUALITY_GATE_RATIONALE,
        "generalization_evidence": False,
        "reviewers": [eval1_name, eval2_name],
        "suite_summary": {
            "expected_cases_count": expected_count,
            "completed_cases_count": completed_count,
            "provisional_passed_count": provisional_passed,
            "provisional_failed_count": provisional_failed,
            "pending_review_count": pending_review,
            "not_generated_count": not_generated,
            "total_score_discrepancies_count": total_discrepancies,
        },
        "pilot_acceptance": {
            "status": acceptance_status,
            "note": "Otomatik pilot kabul durumu geçicidir; nihai onay için insan uzlaşması ve imza gereklidir.",
            "final_signoff": {
                "confirmed": False,
                "status": "pending_human_signoff",
                "signed_off_by": None,
                "signoff_date": None,
                "resolution_notes": None,
            },
        },
        "cases": cases_evaluations,
    }

    return evaluation_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="TryFit Next Pilot Evaluation and Dual Consensus Summary Tool"
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Path to pilot run directory containing pilot-summary.json",
    )
    parser.add_argument(
        "--reviews",
        nargs="*",
        type=Path,
        default=None,
        help="Paths to review CSV files (two files, or single file with two reviewers)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path (defaults to <run-dir>/pilot-evaluation.json)",
    )
    args = parser.parse_args(argv)

    try:
        report = evaluate_pilot_run(args.run_dir, review_paths=args.reviews)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    out_path = args.out or (Path(args.run_dir) / "pilot-evaluation.json")
    write_json(out_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
