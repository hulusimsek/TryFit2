"""Independent 3x3 real-person pilot validation runner.

Supports manifest validation, parsing preflight checks, Phase 1 (FASHN) and
isolated Phase 2 (CatVTON skirt) execution strictly under runs/pilot-*.
Never modifies existing catalog, web app, or prior experiment outputs.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from experiment import METRICS, load_rgb, local_path, sha256, write_json

SAFE_ID_RE = re.compile(r"^[a-z0-9-]+$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_BODY_GROUPS = {"slender", "medium", "fuller"}
ALLOWED_CONSENT_SCOPE = "closed_local_rnd_pilot_only"
ALLOWED_FLOW_ROLES = {"top": "tops", "trousers": "bottoms", "skirt": "bottoms"}
ALLOWED_FLOW_TYPES = {"top_only", "top_plus_trousers", "top_plus_skirt"}
REQUIRED_CORE_FLOWS = {("top_only", None), ("top_plus_trousers", False), ("top_plus_skirt", True)}
SYNTHETIC_MANIFEST_KIND = "synthetic_technical_pilot"
SYNTHETIC_MULTISUBJECT_MANIFEST_KIND = "synthetic_multisubject_pilot"
SYNTHETIC_MANIFEST_KINDS = {SYNTHETIC_MANIFEST_KIND, SYNTHETIC_MULTISUBJECT_MANIFEST_KIND}
SYNTHETIC_PILOT_MODE = "synthetic_technical_rehearsal"
SYNTHETIC_TARGET_ORIGIN = "synthetic_visual_preset"
SYNTHETIC_INDEPENDENT_TARGET_ORIGIN = "synthetic_independent_avatar"
SYNTHETIC_TARGET_ORIGINS = {SYNTHETIC_TARGET_ORIGIN, SYNTHETIC_INDEPENDENT_TARGET_ORIGIN}
REAL_CONSENT_FORBIDDEN_FIELDS = (
    "adult_confirmed",
    "consent_confirmed",
    "consent_record_id",
    "consent_scope",
    "retention_until",
)
SYNTHETIC_FLOW_ROLES = {"top", "skirt"}
SYNTHETIC_FLOW_SIGNATURES = {
    ("top_only", None),
    ("top_plus_skirt", True),
    ("top_plus_skirt", False),
}
SYNTHETIC_INCLUDED_FLOWS = ["top_only", "top_plus_skirt"]
SYNTHETIC_EXCLUDED_FLOWS = ["top_plus_trousers"]
SINGLE_CASE_FASHN_ONLY_MODE = "single_case_fashn_only"
SINGLE_CASE_SKIRT_MODE = "single_case_fashn_and_catvton"
REEXEC_ENV_VAR = "TRYFIT_PILOT_REEXEC"
PARSING_ERROR_PATTERNS = (
    "no upper garment to preserve",
    "no feet to preserve",
    "human parser found no upper garment",
    "target parsing geometry mismatch",
    "invalid target parsing",
    "invalid target human parsing",
    "valid nonempty real human parsing",
    "upper garment, lower body and visible feet required",
)
STAGE2_RESULT_ARTIFACTS = (
    "result.png",
    "comparison.jpg",
    "02-bottom-raw.png",
    "03-protected-outfit.png",
    "upper-protection-mask.png",
    "02-skirt-raw.png",
    "02-skirt-repaint.png",
    "catvton-outcome.json",
)

PILOT_EXTRA_METRICS = (
    "waist_belt_transition",
    "footwear_ankle_transition",
    "stage1_preservation",
)
PILOT_REVIEW_COLUMNS = [
    "id",
    "target_id",
    "flow_id",
    "tuck_top",
    "case_status",
    "reviewer",
    *METRICS,
    *PILOT_EXTRA_METRICS,
    "untargeted_changes",
    "critical_failure",
    "notes",
]
SYNTHETIC_REVIEW_COLUMNS = [
    "id",
    "target_id",
    "flow_id",
    "tuck_top",
    "pilot_mode",
    "generalization_evidence",
    "case_status",
    "reviewer",
    *METRICS,
    *PILOT_EXTRA_METRICS,
    "untargeted_changes",
    "critical_failure",
    "notes",
]
FASHN_SETTINGS = {
    "seed": 42,
    "num_timesteps": 30,
    "guidance_scale": 1.5,
    "segmentation_free": True,
    "num_samples": 1,
}


def _require_nonempty_text(value, message):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(message)
    return value.strip()


def _require_safe_id(value, kind):
    identifier = _require_nonempty_text(value, f"Missing {kind} id.")
    if not SAFE_ID_RE.fullmatch(identifier):
        raise ValueError(f"Invalid {kind} id: {identifier!r}")
    return identifier


def _require_valid_image(root, entry, kind):
    rel = _require_nonempty_text(entry.get("image"), f"{kind} image path missing.")
    path = local_path(root, rel)
    if not path.is_file():
        raise ValueError(f"{kind} image file not found: {rel}")
    digest = _require_nonempty_text(entry.get("image_sha256"), f"{kind} image_sha256 missing.").lower()
    if not SHA256_RE.fullmatch(digest):
        raise ValueError(f"{kind} image_sha256 is not a valid SHA-256 hex digest.")
    actual = sha256(path)
    if actual != digest:
        raise ValueError(f"{kind} image SHA-256 mismatch for {rel}.")
    return path, digest


def _validate_target_common(root, target, identifier):
    if target.get("body_group") not in ALLOWED_BODY_GROUPS:
        raise ValueError(f"Target {identifier}: body_group must be one of {sorted(ALLOWED_BODY_GROUPS)}.")
    if target.get("measured") is not False:
        raise ValueError(f"Target {identifier}: measured must be false.")
    for field in ("pose_notes", "footwear_notes", "current_clothing_notes", "lighting_background_notes"):
        _require_nonempty_text(target.get(field), f"Target {identifier}: {field} is required.")
    _, digest = _require_valid_image(root, target, f"Target {identifier}")
    return digest


def _validate_target(root, target):
    identifier = _require_safe_id(target.get("id"), "target")
    if target.get("target_origin") in SYNTHETIC_TARGET_ORIGINS:
        raise ValueError(f"Target {identifier}: synthetic targets cannot be used in real-person pilot.")
    if target.get("adult_confirmed") is not True:
        raise ValueError(f"Target {identifier}: adult_confirmed must be true.")
    if target.get("consent_confirmed") is not True:
        raise ValueError(f"Target {identifier}: consent_confirmed must be true.")
    _require_nonempty_text(target.get("consent_record_id"), f"Target {identifier}: consent_record_id is required.")
    if target.get("consent_scope") != ALLOWED_CONSENT_SCOPE:
        raise ValueError(f"Target {identifier}: consent_scope must be {ALLOWED_CONSENT_SCOPE!r}.")
    retention = _require_nonempty_text(target.get("retention_until"), f"Target {identifier}: retention_until is required.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retention):
        raise ValueError(f"Target {identifier}: retention_until must be ISO YYYY-MM-DD.")
    try:
        retention_date = date.fromisoformat(retention)
    except ValueError as error:
        raise ValueError(f"Target {identifier}: retention_until must be ISO YYYY-MM-DD.") from error
    if retention_date < date.today():
        raise ValueError(f"Target {identifier}: retention_until {retention} has expired.")
    return _validate_target_common(root, target, identifier)


def _validate_synthetic_target(root, target, baseline_path):
    identifier = _require_safe_id(target.get("id"), "target")
    for forbidden in REAL_CONSENT_FORBIDDEN_FIELDS:
        if forbidden in target:
            raise ValueError(
                f"Synthetic target {identifier}: real consent field {forbidden!r} must not be populated on synthetic avatars."
            )
    expected_origin = SYNTHETIC_TARGET_ORIGIN if baseline_path is not None else SYNTHETIC_INDEPENDENT_TARGET_ORIGIN
    if target.get("target_origin") != expected_origin:
        raise ValueError(f"Synthetic target {identifier}: target_origin must be {expected_origin!r}.")
    if baseline_path is not None:
        derived_from = _require_nonempty_text(
            target.get("derived_from_base_image"),
            f"Synthetic target {identifier}: derived_from_base_image is required.",
        )
        if local_path(root, derived_from) != baseline_path:
            raise ValueError(
                f"Synthetic target {identifier}: derived_from_base_image must match derived_from_baseline."
            )
    else:
        if target.get("derived_from_base_image") is not None:
            raise ValueError(
                f"Synthetic target {identifier}: derived_from_base_image must be null on independent synthetic avatars."
            )
    gen_record = _require_nonempty_text(
        target.get("generation_record"),
        f"Synthetic target {identifier}: generation_record is required.",
    )
    if baseline_path is None and not local_path(root, gen_record).is_file():
        raise ValueError(
            f"Synthetic target {identifier}: generation_record {gen_record!r} does not exist on disk."
        )
    return _validate_target_common(root, target, identifier)


def _validate_trendyol_url(url_text, identifier):
    url = urlparse(_require_nonempty_text(url_text, f"Product {identifier}: product_url is required."))
    host = (url.hostname or "").lower()
    if url.scheme != "https" or not (host == "trendyol.com" or host.endswith(".trendyol.com")) or "-p-" not in url.path:
        raise ValueError(f"Product {identifier}: real Trendyol https://.../product-p-... URL required.")


def _validate_product(root, product):
    identifier = _require_safe_id(product.get("id"), "product")
    _require_nonempty_text(product.get("label"), f"Product {identifier}: label is required.")
    role = product.get("flow_role")
    if role not in ALLOWED_FLOW_ROLES:
        raise ValueError(f"Product {identifier}: unsupported flow_role {role!r}.")
    if product.get("category") != ALLOWED_FLOW_ROLES[role]:
        raise ValueError(f"Product {identifier}: category {product.get('category')!r} does not match flow_role {role!r}.")
    if product.get("garment_photo_type") != "model":
        raise ValueError(f"Product {identifier}: flat-lay or non-model garment photos are not allowed in this pilot.")
    if product.get("photo_origin") != "real_model_photo":
        raise ValueError(f"Product {identifier}: photo_origin must be 'real_model_photo'.")
    if product.get("listing_ai_generated_label_observed") is not False:
        raise ValueError(f"Product {identifier}: AI-generated listing imagery is disallowed in this pilot.")
    _validate_trendyol_url(product.get("product_url"), identifier)
    _require_nonempty_text(product.get("source_image_url"), f"Product {identifier}: source_image_url is required.")
    _require_nonempty_text(product.get("source_notes"), f"Product {identifier}: source_notes is required.")
    _, digest = _require_valid_image(root, product, f"Product {identifier}")
    return role, digest


def _validate_flow(flow, product_by_id):
    identifier = _require_safe_id(flow.get("id"), "flow")
    flow_type = flow.get("flow_type")
    if flow_type not in ALLOWED_FLOW_TYPES:
        raise ValueError(f"Flow {identifier}: unsupported flow_type {flow_type!r}.")
    top_id = flow.get("top_id")
    if top_id not in product_by_id or product_by_id[top_id]["flow_role"] != "top":
        raise ValueError(f"Flow {identifier}: valid top product required.")
    bottom_id = flow.get("bottom_id")
    tuck_top = flow.get("tuck_top")
    if flow_type == "top_only":
        if bottom_id is not None or tuck_top not in (None, False):
            raise ValueError(f"Flow {identifier}: top_only cannot specify bottom_id or tuck_top=true.")
        return identifier, (flow_type, None)
    if flow_type == "top_plus_trousers":
        if bottom_id not in product_by_id or product_by_id[bottom_id]["flow_role"] != "trousers":
            raise ValueError(f"Flow {identifier}: valid trousers product required.")
        if tuck_top not in (None, False):
            raise ValueError(f"Flow {identifier}: tuck_top is unsupported for trousers.")
        return identifier, (flow_type, False)
    if bottom_id not in product_by_id or product_by_id[bottom_id]["flow_role"] != "skirt":
        raise ValueError(f"Flow {identifier}: valid skirt product required.")
    if not isinstance(tuck_top, bool):
        raise ValueError(f"Flow {identifier}: explicit boolean tuck_top required for skirt.")
    return identifier, (flow_type, tuck_top)


def _validate_targets_group(root, targets, *, synthetic=False, baseline_path=None):
    target_ids, target_hashes, target_body_groups = set(), set(), set()
    for target in targets:
        if synthetic:
            digest = _validate_synthetic_target(root, target, baseline_path)
        else:
            digest = _validate_target(root, target)
        tid = target["id"]
        if tid in target_ids:
            raise ValueError(f"Duplicate target id: {tid}")
        if digest in target_hashes:
            raise ValueError(f"Duplicate target image content detected for {tid}.")
        group = target["body_group"]
        if group in target_body_groups:
            raise ValueError(f"Duplicate target body_group {group!r}; three distinct groups required.")
        target_ids.add(tid)
        target_hashes.add(digest)
        target_body_groups.add(group)
    if target_body_groups != ALLOWED_BODY_GROUPS:
        raise ValueError("Pilot targets must cover each body_group exactly once: fuller, medium, slender.")


def _validate_products_group(root, products, *, expected_roles):
    product_ids, product_roles, product_hashes = set(), set(), set()
    product_by_id = {}
    for product in products:
        role, digest = _validate_product(root, product)
        pid = product["id"]
        if pid in product_ids or role in product_roles or digest in product_hashes:
            raise ValueError(f"Products must have unique ids, flow_roles, and images ({pid}).")
        if role not in expected_roles:
            raise ValueError(f"Product {pid}: flow_role {role!r} is outside allowed roles {sorted(expected_roles)}.")
        product_ids.add(pid)
        product_roles.add(role)
        product_hashes.add(digest)
        product_by_id[pid] = product
    if product_roles != expected_roles:
        raise ValueError(f"Products must cover exact flow roles: {sorted(expected_roles)}.")
    return product_by_id


def _validate_flows_group(flows, product_by_id, *, required_signatures, label):
    if len(flows) != len(required_signatures):
        raise ValueError(f"{label} must contain exactly {len(required_signatures)} flows.")
    seen_flow_ids = set()
    signatures = set()
    for flow in flows:
        fid, signature = _validate_flow(flow, product_by_id)
        if fid in seen_flow_ids:
            raise ValueError(f"Duplicate flow id: {fid}")
        if signature in signatures:
            raise ValueError(f"Duplicate flow definition for {signature}.")
        seen_flow_ids.add(fid)
        signatures.add(signature)
    if signatures != required_signatures:
        raise ValueError(f"{label} must match exact flow signatures {sorted(required_signatures)}.")
    return seen_flow_ids


def validate_pilot_manifest(manifest, root):
    """Validate 3x3 real-person pilot manifest rules without touching GPU."""
    root = Path(root).resolve()
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported pilot manifest schema_version.")
    if (
        manifest.get("manifest_kind") in SYNTHETIC_MANIFEST_KINDS
        or manifest.get("generalization_evidence") is False
        or manifest.get("same_base_identity") in (True, False)
    ):
        raise ValueError("Synthetic technical pilot manifests cannot pass real-person pilot validation; use --synthetic-tech.")
    targets = manifest.get("targets")
    products = manifest.get("products")
    flows = manifest.get("flows")
    optional_controls = manifest.get("optional_controls", [])
    if not isinstance(targets, list) or len(targets) != 3:
        raise ValueError("Pilot manifest requires exactly 3 distinct adult target entries.")
    if not isinstance(products, list) or len(products) != 3:
        raise ValueError("Pilot manifest requires exactly 3 products (top, trousers, skirt).")
    if not isinstance(flows, list) or not isinstance(optional_controls, list):
        raise ValueError("Pilot manifest flows and optional_controls must be lists.")

    _validate_targets_group(root, targets, synthetic=False)
    product_by_id = _validate_products_group(root, products, expected_roles=set(ALLOWED_FLOW_ROLES))
    seen_flow_ids = _validate_flows_group(
        flows,
        product_by_id,
        required_signatures=REQUIRED_CORE_FLOWS,
        label="Core flows",
    )

    control_signatures = set()
    for control in optional_controls:
        fid, signature = _validate_flow(control, product_by_id)
        if fid in seen_flow_ids:
            raise ValueError(f"Duplicate optional control flow id: {fid}")
        if signature != ("top_plus_skirt", False):
            raise ValueError(f"Optional control {fid}: only top_plus_skirt with tuck_top=false is allowed.")
        if signature in control_signatures:
            raise ValueError(f"Duplicate optional control definition for {fid}.")
        seen_flow_ids.add(fid)
        control_signatures.add(signature)

    return {"targets": targets, "products": products, "product_by_id": product_by_id,
            "flows": flows, "optional_controls": optional_controls}


def validate_synthetic_pilot_manifest(manifest, root):
    """Validate isolated 2-flow synthetic technical rehearsal manifest rules."""
    root = Path(root).resolve()
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported synthetic pilot manifest schema_version.")
    kind = manifest.get("manifest_kind")
    if kind not in SYNTHETIC_MANIFEST_KINDS:
        raise ValueError(f"Synthetic pilot manifest requires manifest_kind in {sorted(SYNTHETIC_MANIFEST_KINDS)!r}.")
    if manifest.get("generalization_evidence") is not False:
        raise ValueError("Synthetic pilot manifest must explicitly declare generalization_evidence: false.")
    if kind == SYNTHETIC_MANIFEST_KIND:
        if manifest.get("same_base_identity") is not True:
            raise ValueError("Synthetic pilot manifest must explicitly declare same_base_identity: true.")
        if manifest.get("effective_subject_diversity") != 1:
            raise ValueError("Synthetic pilot manifest must explicitly declare effective_subject_diversity: 1.")
        baseline = _require_nonempty_text(
            manifest.get("derived_from_baseline"),
            "Synthetic pilot manifest requires derived_from_baseline.",
        )
        baseline_path = local_path(root, baseline)
    else:
        if manifest.get("same_base_identity") is not False:
            raise ValueError("Multi-subject synthetic pilot manifest must explicitly declare same_base_identity: false.")
        if manifest.get("effective_subject_diversity") != 3:
            raise ValueError("Multi-subject synthetic pilot manifest must explicitly declare effective_subject_diversity: 3.")
        if manifest.get("derived_from_baseline") is not None:
            raise ValueError("Multi-subject synthetic pilot manifest requires derived_from_baseline: null.")
        baseline_path = None
    if manifest.get("included_flows") != SYNTHETIC_INCLUDED_FLOWS:
        raise ValueError(f"Synthetic pilot manifest included_flows must be {SYNTHETIC_INCLUDED_FLOWS!r}.")
    if manifest.get("excluded_flows") != SYNTHETIC_EXCLUDED_FLOWS:
        raise ValueError(f"Synthetic pilot manifest excluded_flows must be {SYNTHETIC_EXCLUDED_FLOWS!r}.")

    targets = manifest.get("targets")
    products = manifest.get("products")
    flows = manifest.get("flows")
    optional_controls = manifest.get("optional_controls", [])
    if not isinstance(targets, list) or len(targets) != 3:
        raise ValueError("Synthetic pilot manifest requires exactly 3 synthetic targets.")
    if not isinstance(products, list) or len(products) != 2:
        raise ValueError("Synthetic 2-flow pilot requires exactly 2 products (top and skirt; trousers excluded).")
    if not isinstance(flows, list) or not isinstance(optional_controls, list):
        raise ValueError("Synthetic pilot manifest flows and optional_controls must be lists.")
    if optional_controls:
        raise ValueError("Synthetic 2-flow pilot disallows optional_controls; include both skirt tuck modes in flows.")

    _validate_targets_group(root, targets, synthetic=True, baseline_path=baseline_path)
    product_by_id = _validate_products_group(root, products, expected_roles=SYNTHETIC_FLOW_ROLES)
    _validate_flows_group(
        flows,
        product_by_id,
        required_signatures=SYNTHETIC_FLOW_SIGNATURES,
        label="Synthetic 2-flow pilot flows",
    )

    return {"targets": targets, "products": products, "product_by_id": product_by_id,
            "flows": flows, "optional_controls": []}


def _validate_manifest_for_mode(manifest, root, *, synthetic_tech=False):
    if synthetic_tech:
        return validate_synthetic_pilot_manifest(manifest, root)
    return validate_pilot_manifest(manifest, root)


def _assert_mode_consistency(manifest, summary=None, *, synthetic_tech=False):
    if synthetic_tech:
        kind = manifest.get("manifest_kind")
        if kind not in SYNTHETIC_MANIFEST_KINDS:
            raise ValueError("Synthetic phase requires a synthetic technical manifest.")
        if summary is not None:
            sum_kind = summary.get("manifest_kind")
            if (
                summary.get("pilot_mode") != SYNTHETIC_PILOT_MODE
                or sum_kind not in SYNTHETIC_MANIFEST_KINDS
                or summary.get("generalization_evidence") is not False
            ):
                raise ValueError("Run directory pilot-summary.json is not a valid synthetic technical rehearsal.")
            if sum_kind == SYNTHETIC_MANIFEST_KIND and (
                summary.get("same_base_identity") is not True
                or summary.get("effective_subject_diversity") != 1
            ):
                raise ValueError("Run directory pilot-summary.json is not a valid synthetic technical rehearsal.")
            if sum_kind == SYNTHETIC_MULTISUBJECT_MANIFEST_KIND and (
                summary.get("same_base_identity") is not False
                or summary.get("effective_subject_diversity") != 3
            ):
                raise ValueError("Run directory pilot-summary.json is not a valid synthetic multi-subject technical rehearsal.")
        if summary is not None and summary.get("single_case_mode"):
            cases = summary.get("cases") or []
            selected_id = summary.get("selected_case_id")
            exec_mode = summary.get("execution_mode")
            if len(cases) != 1 or not selected_id or cases[0].get("id") != selected_id:
                raise ValueError("Run directory pilot-summary.json has an invalid single-case selection.")
            flow_type = cases[0].get("flow_type")
            if exec_mode == SINGLE_CASE_FASHN_ONLY_MODE:
                if summary.get("catvton_skipped") is not True or flow_type != "top_only":
                    raise ValueError("Run directory pilot-summary.json has an invalid single-case FASHN-only configuration.")
            elif exec_mode == SINGLE_CASE_SKIRT_MODE:
                if summary.get("catvton_skipped") is not False or flow_type != "top_plus_skirt":
                    raise ValueError("Run directory pilot-summary.json has an invalid single-case FASHN+CatVTON configuration.")
            else:
                raise ValueError("Run directory pilot-summary.json has an invalid single-case execution_mode.")
        return
    if (
        manifest.get("manifest_kind") in SYNTHETIC_MANIFEST_KINDS
        or manifest.get("generalization_evidence") is False
        or manifest.get("same_base_identity") in (True, False)
    ):
        raise ValueError("Synthetic technical pilot manifest cannot execute without --synthetic-tech.")
    if summary is not None and (
        "pilot_mode" in summary
        or summary.get("single_case_mode")
        or summary.get("manifest_kind") in SYNTHETIC_MANIFEST_KINDS
        or summary.get("generalization_evidence") is False
        or summary.get("same_base_identity") in (True, False)
    ):
        raise ValueError("Synthetic technical rehearsal run directory cannot execute without --synthetic-tech.")


def verify_pilot_extractions(root, products):
    """Verify SAM2 extraction artifacts before instantiating any GPU model."""
    root = Path(root).resolve()
    provenance = {}
    for product in products:
        extraction_dir = local_path(root, f"runs/source-extraction-{product['id']}-refined")
        meta_path = extraction_dir / "extraction.json"
        mask_path = extraction_dir / "mask.png"
        if not meta_path.is_file() or not mask_path.is_file():
            raise ValueError(f"Missing SAM2 extraction artifacts for product {product['id']}: {extraction_dir}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        annotation = meta.get("annotation", {})
        if (annotation.get("id") != product["id"]
                or annotation.get("category") != product["category"]
                or annotation.get("image_sha256") != product["image_sha256"]
                or sha256(mask_path) != meta.get("mask_sha256")):
            raise ValueError(f"Source extraction provenance mismatch for product {product['id']}.")
        provenance[product["id"]] = {
            "directory": extraction_dir.relative_to(root).as_posix(),
            "mask_sha256": meta["mask_sha256"],
        }
    return provenance


def inspect_parsing(labels):
    """Audit fashn-human-parser output against trousers and skirt runtime requirements."""
    labels = np.asarray(labels)
    if labels.ndim != 2 or not np.isin(labels, np.arange(18)).all():
        raise ValueError("Invalid target human parsing mask.")
    total = float(labels.size)
    has_upper = bool((labels == 3).any())
    has_lower = bool(np.isin(labels, [5, 6, 7, 14]).any())
    has_feet = bool((labels == 15).any())
    missing_trousers = [label for label, ok in ((3, has_upper), (15, has_feet)) if not ok]
    missing_skirt = [label for label, ok in ((3, has_upper), ("5|6|7|14", has_lower), (15, has_feet)) if not ok]
    return {
        "shape": [int(labels.shape[0]), int(labels.shape[1])],
        "has_upper": has_upper,
        "has_lower": has_lower,
        "has_feet": has_feet,
        "fractions": {
            "upper_3": round(float((labels == 3).sum()) / total, 5),
            "lower_5_6_7_14": round(float(np.isin(labels, [5, 6, 7, 14]).sum()) / total, 5),
            "feet_15": round(float((labels == 15).sum()) / total, 5),
        },
        "missing_for_trousers_preservation": missing_trousers,
        "missing_for_skirt_envelope": missing_skirt,
        "passed_trousers_requirements": not missing_trousers,
        "passed_skirt_requirements": not missing_skirt,
    }


def _save_parsing_preview(labels, destination):
    palette = np.zeros((*labels.shape, 3), dtype=np.uint8)
    palette[labels == 3] = [60, 140, 240]
    palette[np.isin(labels, [5, 6, 7, 14])] = [60, 190, 110]
    palette[labels == 15] = [240, 90, 60]
    palette[np.isin(labels, [1, 2, 12, 13, 16])] = [200, 180, 90]
    Image.fromarray(palette).save(destination)


def _is_parsing_error(error):
    """Return True only for known target human-parsing failures, never generic pipeline errors."""
    if not isinstance(error, ValueError):
        return False
    message = str(error).lower()
    return any(pattern in message for pattern in PARSING_ERROR_PATTERNS)


def _safe_inspect_and_save_parsing(hp_model, image_rgb, *, json_path=None, preview_path=None):
    """Run parsing and `inspect_parsing` safely without masking primary errors."""
    try:
        labels = np.asarray(hp_model.predict(np.asarray(image_rgb)))
    except Exception as audit_error:
        info = {
            "valid": False,
            "passed_trousers_requirements": False,
            "passed_skirt_requirements": False,
            "audit_error": str(audit_error),
        }
        if json_path is not None:
            write_json(json_path, info)
        return None, info
    try:
        info = inspect_parsing(labels)
    except ValueError as audit_error:
        info = {
            "valid": False,
            "shape": [int(dim) for dim in labels.shape],
            "dtype": str(labels.dtype),
            "passed_trousers_requirements": False,
            "passed_skirt_requirements": False,
            "audit_error": str(audit_error),
        }
        if json_path is not None:
            write_json(json_path, info)
        return None, info
    info["valid"] = True
    if preview_path is not None:
        _save_parsing_preview(labels, preview_path)
    if json_path is not None:
        write_json(json_path, info)
    return labels, info


def _audit_post_top_parsing(case_dir, case_record, hp_model, top_path):
    """Safely inspect post-top parsing and save diagnostics without masking primary errors."""
    labels, info = _safe_inspect_and_save_parsing(
        hp_model,
        load_rgb(top_path),
        json_path=case_dir / "parsing-post-top.json",
        preview_path=case_dir / "parsing-post-top.png",
    )
    case_record["parsing_post_top"] = info
    return labels, info


def _cleanup_stage2_artifacts(case_dir, *, final_status, reason):
    """Remove misleading Stage 2 outputs and synchronize case run.json on non-completed cases."""
    for name in STAGE2_RESULT_ARTIFACTS:
        artifact = case_dir / name
        if artifact.is_file():
            artifact.unlink()
    run_meta_path = case_dir / "run.json"
    if run_meta_path.is_file():
        run_meta = json.loads(run_meta_path.read_text(encoding="utf-8"))
        run_meta["status"] = final_status
        run_meta["error"] = reason
        run_meta.pop("output_sha256", None)
        write_json(run_meta_path, run_meta)


def _venv_python(root, venv_name, *, platform=None):
    """Return the platform-appropriate Python executable path inside `root / venv_name`."""
    target_platform = sys.platform if platform is None else platform
    rel = Path("Scripts/python.exe") if target_platform == "win32" else Path("bin/python")
    return Path(root).resolve() / venv_name / rel


def _require_venv_python(root, venv_name):
    """Require an existing Python executable inside `root / venv_name`."""
    python_path = _venv_python(root, venv_name)
    if not python_path.is_file():
        raise FileNotFoundError(f"Isolated environment unavailable: {python_path}")
    return python_path


def _norm_path(path):
    return os.path.normcase(os.path.abspath(str(path)))


def _is_current_venv(root, venv_name):
    """Return True when the active interpreter belongs to `root / venv_name`."""
    expected_dir = Path(root).resolve() / venv_name
    expected_exe = _venv_python(root, venv_name)
    return (
        _norm_path(sys.prefix) == _norm_path(expected_dir)
        or _norm_path(sys.executable) == _norm_path(expected_exe)
    )


def _ensure_cli_venv(root, venv_name, argv, *, subprocess_runner=None):
    """Ensure a CLI subcommand executes under `root / venv_name`, redirecting once if safe."""
    if _is_current_venv(root, venv_name):
        return
    expected_exe = _require_venv_python(root, venv_name)
    if os.environ.get(REEXEC_ENV_VAR) == venv_name:
        raise RuntimeError(
            f"Pilot CLI failed to enter {venv_name} interpreter ({expected_exe}); "
            f"active interpreter is {sys.executable}."
        )
    runner = subprocess_runner or subprocess.run
    env = dict(os.environ)
    env[REEXEC_ENV_VAR] = venv_name
    completed = runner(
        [str(expected_exe), "-u", str(Path(__file__).resolve()), *argv],
        env=env,
        check=False,
    )
    raise SystemExit(completed.returncode)


def run_parsing_preflight(root, targets, hp_model, preflight_dir):
    """Inspect real targets with human parsing and store diagnostics cleanly."""
    root = Path(root).resolve()
    preflight_dir = Path(preflight_dir)
    preflight_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for target in targets:
        picture = load_rgb(local_path(root, target["image"]))
        preview = preflight_dir / f"{target['id']}-parsing.png"
        labels, info = _safe_inspect_and_save_parsing(hp_model, picture, preview_path=preview)
        if labels is not None:
            info["preview"] = preview.relative_to(preflight_dir.parent).as_posix()
        info["image_size"] = list(picture.size)
        report[target["id"]] = info
    return report


def _create_pilot_dir(root):
    runs_dir = Path(root).resolve() / "runs"
    runs_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = runs_dir / f"pilot-{stamp}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _assert_pilot_run_dir(root, run_dir):
    root = Path(root).resolve()
    resolved = Path(run_dir).resolve()
    runs_root = (root / "runs").resolve()
    if resolved.parent != runs_root or not resolved.name.startswith("pilot-"):
        raise ValueError("Pilot runner outputs are strictly confined to runs/pilot-* directories.")
    return resolved


def expand_pilot_cases(manifest, *, include_untucked=False, case_id=None):
    """Expand 3 targets x 3 flows (+ optional untucked controls) deterministically."""
    flows = list(manifest["flows"])
    if include_untucked:
        flows.extend(manifest.get("optional_controls", []))
    cases = []
    for target in manifest["targets"]:
        for flow in flows:
            cases.append({
                "id": f"{target['id']}__{flow['id']}",
                "target_id": target["id"],
                "flow_id": flow["id"],
                "flow_type": flow["flow_type"],
                "top_id": flow["top_id"],
                "bottom_id": flow.get("bottom_id"),
                "tuck_top": flow.get("tuck_top"),
                "status": "pending",
            })
    if case_id is not None:
        return [_select_single_case(cases, case_id)]
    return cases


def _select_single_case(cases, case_id):
    selector = _require_nonempty_text(case_id, "Case selector (--case) must be a non-empty '<target_id>__<flow_id>' value.")
    matches = [case for case in cases if case["id"] == selector]
    if not matches:
        available = ", ".join(case["id"] for case in cases)
        raise ValueError(f"Unknown case selector {selector!r}; defined cases: {available}")
    if len(matches) > 1:
        raise ValueError(f"Ambiguous case selector {selector!r}; matched {len(matches)} cases.")
    selected = dict(matches[0])
    if selected["flow_type"] == "top_only":
        selected.update(
            single_case_mode=True,
            execution_mode=SINGLE_CASE_FASHN_ONLY_MODE,
            catvton_skipped=True,
            catvton_skip_reason="Single-case FASHN-only mode (--case): CatVTON Phase 2 intentionally skipped.",
        )
        return selected
    if selected["flow_type"] == "top_plus_skirt":
        selected.update(
            single_case_mode=True,
            execution_mode=SINGLE_CASE_SKIRT_MODE,
            fashn_executed=False,
            catvton_executed=False,
            catvton_skipped=False,
        )
        return selected
    raise ValueError(
        f"Single-case mode (--case) does not support flow_type={selected['flow_type']!r} for {selector!r}."
    )


def _save_case_comparison(root, target, products, result_path, destination):
    panels = [("TARGET", load_rgb(local_path(root, target["image"])))]
    for label, product in products:
        panels.append((label, load_rgb(local_path(root, product["image"]))))
    panels.append(("RESULT", load_rgb(result_path)))
    board = Image.new("RGB", (len(panels) * 320, 520), "#f5f5f5")
    draw = ImageDraw.Draw(board)
    for idx, (title, pic) in enumerate(panels):
        thumb = ImageOps.contain(pic, (312, 480))
        board.paste(thumb, (idx * 320 + (320 - thumb.width) // 2, 30 + (480 - thumb.height) // 2))
        draw.text((idx * 320 + 8, 8), title, fill="#111111")
    board.save(destination)


def _create_review_template(run_dir, cases, *, synthetic_tech=False):
    rows = []
    fieldnames = SYNTHETIC_REVIEW_COLUMNS if synthetic_tech else PILOT_REVIEW_COLUMNS
    for case in cases:
        status = case["status"]
        note = ""
        if status == "parse_blocked":
            note = f"parse_blocked: {case.get('error', '')}".strip()
        elif status != "completed":
            note = f"{status}: {case.get('error', '')}".strip()
        elif case.get("single_case_mode") or case.get("catvton_skipped"):
            if case.get("execution_mode") == SINGLE_CASE_SKIRT_MODE:
                note = (
                    f"single_case_mode=true; execution_mode={SINGLE_CASE_SKIRT_MODE}; "
                    f"selected_case_id={case['id']}; "
                    f"fashn_executed={str(bool(case.get('fashn_executed'))).lower()}; "
                    f"catvton_executed={str(bool(case.get('catvton_executed'))).lower()}; "
                    "catvton_skipped=false; generalization_evidence=false"
                )
            else:
                note = "single_case_fashn_only; catvton_skipped=true"
        row = {
            "id": case["id"],
            "target_id": case["target_id"],
            "flow_id": case["flow_id"],
            "tuck_top": "" if case["tuck_top"] is None else str(case["tuck_top"]).lower(),
            "case_status": status,
            "reviewer": "",
            **{col: "" for col in METRICS},
            **{col: ("N/A" if case["flow_type"] == "top_only" else "") for col in PILOT_EXTRA_METRICS},
            "untargeted_changes": "",
            "critical_failure": "",
            "notes": note,
        }
        if synthetic_tech:
            row["pilot_mode"] = SYNTHETIC_PILOT_MODE
            row["generalization_evidence"] = "false"
        rows.append(row)
    path = Path(run_dir) / "review-template.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _refresh_summary(root, run_dir, summary):
    counts = {}
    for case in summary["cases"]:
        counts[case["status"]] = counts.get(case["status"], 0) + 1
    summary["counts"] = counts
    write_json(run_dir / "pilot-summary.json", summary)
    _create_review_template(
        run_dir,
        summary["cases"],
        synthetic_tech=(summary.get("pilot_mode") == SYNTHETIC_PILOT_MODE),
    )


def _run_top_only_case(root, target, top_product, case_dir, pipeline, case_record, *, synthetic_tech=False):
    case_dir.mkdir(parents=True, exist_ok=True)
    target_path = local_path(root, target["image"])
    top_path = local_path(root, top_product["image"])
    selection = {"target": target, "items": [top_product], "flow_type": "top_only"}
    if synthetic_tech:
        selection["pilot_mode"] = SYNTHETIC_PILOT_MODE
        selection["generalization_evidence"] = False
    if case_record.get("single_case_mode"):
        selection["single_case_mode"] = True
        selection["execution_mode"] = "single_case_fashn_only"
        selection["catvton_skipped"] = bool(case_record.get("catvton_skipped", True))
    write_json(case_dir / "selection.json", selection)
    start = time.perf_counter()
    output = pipeline(
        person_image=load_rgb(target_path),
        garment_image=load_rgb(top_path),
        category="tops",
        garment_photo_type=top_product["garment_photo_type"],
        **FASHN_SETTINGS,
    ).images[0]
    top_out = case_dir / "01-top.png"
    result_out = case_dir / "result.png"
    output.save(top_out)
    shutil.copy2(top_out, result_out)
    case_record.update(
        status="completed",
        elapsed_seconds=round(time.perf_counter() - start, 2),
        result=result_out.relative_to(case_dir.parents[1]).as_posix(),
        output_sha256=sha256(result_out),
    )


def _run_trousers_case(root, target, top_product, bottom_product, case_dir, pipeline, case_record):
    from protect_outfit import compose_outfit
    from upper_preservation import preservation_alpha

    case_dir.mkdir(parents=True, exist_ok=True)
    target_path = local_path(root, target["image"])
    selection = {"target": target, "items": [top_product, bottom_product], "flow_type": "top_plus_trousers"}
    try:
        compose_outfit(
            root,
            target_path,
            top_product,
            bottom_product,
            case_dir,
            pipeline=pipeline,
            extra_metadata={"pilot_case": case_record["id"], "preserve_feet": True},
            bottom_segmentation_free=True,
            selection_record=selection,
            selection_sha256=sha256(case_dir.parents[1] / "manifest.json"),
            avatar_profile={"id": target["id"], "measured": False},
        )
    except Exception as error:
        top_path = case_dir / "01-top.png"
        if _is_parsing_error(error):
            if top_path.is_file():
                _audit_post_top_parsing(case_dir, case_record, pipeline.hp_model, top_path)
            _cleanup_stage2_artifacts(case_dir, final_status="parse_blocked", reason=str(error))
            case_record.update(status="parse_blocked", error=str(error))
            return
        _cleanup_stage2_artifacts(case_dir, final_status="failed", reason=str(error))
        raise

    # Verify top-stage parsing explicitly so mock/no-op pipelines cannot mask missing labels.
    top_path = case_dir / "01-top.png"
    labels, info = _audit_post_top_parsing(case_dir, case_record, pipeline.hp_model, top_path)
    if labels is None:
        reason = info.get("audit_error") or "Invalid post-top parsing mask."
        _cleanup_stage2_artifacts(case_dir, final_status="parse_blocked", reason=reason)
        case_record.update(status="parse_blocked", error=reason)
        return
    try:
        preservation_alpha(labels, preserve_feet=True)
    except ValueError as error:
        _cleanup_stage2_artifacts(case_dir, final_status="parse_blocked", reason=str(error))
        case_record.update(status="parse_blocked", parsing_post_top=info, error=str(error))
        return

    raw_bottom = case_dir / "02-bottom-raw.png"
    result_out = case_dir / "result.png"
    shutil.copy2(raw_bottom, result_out)
    run_meta = json.loads((case_dir / "run.json").read_text(encoding="utf-8"))
    elapsed = sum(step.get("elapsed_seconds", 0.0) for step in run_meta.get("steps", []))
    case_record.update(
        status="completed",
        parsing_post_top=info,
        elapsed_seconds=round(elapsed, 2),
        result=result_out.relative_to(case_dir.parents[1]).as_posix(),
        output_sha256=sha256(result_out),
    )


def _prepare_skirt_case(root, target, top_product, skirt_product, case_dir, pipeline, case_record, *, synthetic_tech=False):
    from catvton_skirt_probe import prepare_source
    from local_skirt_inputs import prepare_skirt_masks

    case_dir.mkdir(parents=True, exist_ok=True)
    target_path = local_path(root, target["image"])
    top_path = local_path(root, top_product["image"])
    selection = {
        "target": target,
        "items": [top_product, skirt_product],
        "flow_type": "top_plus_skirt",
        "tuck_top": bool(case_record["tuck_top"]),
    }
    if synthetic_tech:
        selection["pilot_mode"] = SYNTHETIC_PILOT_MODE
        selection["generalization_evidence"] = False
    if case_record.get("single_case_mode"):
        selection["single_case_mode"] = True
        selection["execution_mode"] = SINGLE_CASE_SKIRT_MODE
        selection["selected_case_id"] = case_record["id"]
        selection["fashn_executed"] = False
        selection["catvton_executed"] = False
        selection["catvton_skipped"] = bool(case_record.get("catvton_skipped", False))
    write_json(case_dir / "selection.json", selection)

    start = time.perf_counter()
    top_image = pipeline(
        person_image=load_rgb(target_path),
        garment_image=load_rgb(top_path),
        category="tops",
        garment_photo_type=top_product["garment_photo_type"],
        **FASHN_SETTINGS,
    ).images[0]
    top_image.save(case_dir / "01-top.png")
    if case_record.get("single_case_mode"):
        case_record["fashn_executed"] = True
        selection["fashn_executed"] = True
        write_json(case_dir / "selection.json", selection)

    labels, info = _audit_post_top_parsing(case_dir, case_record, pipeline.hp_model, case_dir / "01-top.png")
    elapsed = round(time.perf_counter() - start, 2)
    if labels is None:
        reason = info.get("audit_error") or "Invalid post-top parsing mask."
        _cleanup_stage2_artifacts(case_dir, final_status="parse_blocked", reason=reason)
        case_record.update(status="parse_blocked", upper_elapsed_seconds=elapsed, error=reason)
        return
    try:
        masks = prepare_skirt_masks(
            top_image, labels, tuck_top=bool(case_record["tuck_top"]), case_id=case_record.get("id")
        )
        target_canvas, hard, soft, preserve, overlay, annotation, transform = masks
    except ValueError as error:
        _cleanup_stage2_artifacts(case_dir, final_status="parse_blocked", reason=str(error))
        case_record.update(
            status="parse_blocked",
            parsing_post_top=info,
            upper_elapsed_seconds=elapsed,
            error=str(error),
        )
        return

    condition, source_meta = prepare_source(root, skirt_product)
    repaint_mask = getattr(masks, "repaint_soft", soft)

    for name, image in (
        ("cat-target.png", target_canvas),
        ("cat-hard-mask.png", hard),
        ("cat-soft-mask.png", soft),
        ("cat-preserve.png", preserve),
        ("cat-mask-preview.jpg", overlay),
        ("cat-condition.png", condition),
        ("cat-repaint-mask.png", repaint_mask),
    ):
        image.save(case_dir / name)

    files = [
        "01-top.png",
        "cat-target.png",
        "cat-hard-mask.png",
        "cat-soft-mask.png",
        "cat-preserve.png",
        "cat-condition.png",
        "cat-repaint-mask.png",
    ]
    write_json(
        case_dir / "skirt-handoff.json",
        {
            "selection_sha256": sha256(case_dir / "selection.json"),
            "files": {name: sha256(case_dir / name) for name in files},
            "annotation": annotation,
            "target_transform": transform,
            "source": source_meta,
            "upper_elapsed_seconds": round(time.perf_counter() - start, 2),
        },
    )
    case_record.update(
        status="prepared",
        parsing_post_top=info,
        upper_elapsed_seconds=round(time.perf_counter() - start, 2),
        handoff_sha256=sha256(case_dir / "skirt-handoff.json"),
    )


def run_fashn_phase(root, run_dir, *, fashn_factory=None, synthetic_tech=False):
    """Execute preflight parsing and Phase 1 FASHN stages inside .venv."""
    root = Path(root).resolve()
    if fashn_factory is None and not _is_current_venv(root, ".venv"):
        venv_python = _venv_python(root, ".venv")
        raise RuntimeError(
            f"FASHN phase requires {venv_python} (active interpreter: {sys.executable})."
        )
    run_dir = _assert_pilot_run_dir(root, run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
    _assert_mode_consistency(manifest, summary, synthetic_tech=synthetic_tech)
    validated = _validate_manifest_for_mode(manifest, root, synthetic_tech=synthetic_tech)
    extractions = verify_pilot_extractions(root, validated["products"])
    summary["source_extractions"] = extractions

    if fashn_factory is None:
        from masked_outfit import MaskedOutfitPipeline
        pipeline = MaskedOutfitPipeline(
            root,
            validated["products"],
            allow_masked_target=True,
            preserve_upper=True,
            preserve_feet=True,
        )
    else:
        pipeline = fashn_factory(root, validated["products"])

    targets_by_id = {t["id"]: t for t in validated["targets"]}
    products_by_id = validated["product_by_id"]

    is_single_case = bool(summary.get("single_case_mode"))
    if is_single_case:
        exec_mode = summary.get("execution_mode")
        if len(summary["cases"]) != 1:
            raise ValueError("Single-case mode requires exactly 1 case.")
        case_flow_type = summary["cases"][0]["flow_type"]
        if exec_mode == SINGLE_CASE_FASHN_ONLY_MODE and case_flow_type != "top_only":
            raise ValueError("Single-case FASHN-only mode cannot execute non-top_only cases.")
        if exec_mode == SINGLE_CASE_SKIRT_MODE and case_flow_type != "top_plus_skirt":
            raise ValueError("Single-case FASHN+CatVTON mode requires a top_plus_skirt case.")
        if exec_mode not in {SINGLE_CASE_FASHN_ONLY_MODE, SINGLE_CASE_SKIRT_MODE}:
            raise ValueError(f"Unsupported single-case execution_mode: {exec_mode!r}")
        preflight_target_ids = list(dict.fromkeys(c["target_id"] for c in summary["cases"]))
        preflight_targets = [targets_by_id[tid] for tid in preflight_target_ids]
    else:
        preflight_targets = validated["targets"]

    preflight = run_parsing_preflight(root, preflight_targets, pipeline.hp_model, run_dir / "preflight")
    write_json(run_dir / "parsing-preflight.json", preflight)
    summary["parsing_preflight"] = preflight
    _refresh_summary(root, run_dir, summary)

    for index, case in enumerate(summary["cases"]):
        target = targets_by_id[case["target_id"]]
        top_product = products_by_id[case["top_id"]]
        case_dir = run_dir / "cases" / case["id"]
        try:
            if case["flow_type"] == "top_only":
                _run_top_only_case(
                    root,
                    target,
                    top_product,
                    case_dir,
                    pipeline,
                    case,
                    synthetic_tech=synthetic_tech,
                )
                if case["status"] == "completed":
                    try:
                        _save_case_comparison(root, target, [("TOP SOURCE", top_product)], case_dir / "result.png", case_dir / "comparison.jpg")
                    except Exception as error:
                        case["comparison_error"] = str(error)
            elif case["flow_type"] == "top_plus_trousers":
                bottom_product = products_by_id[case["bottom_id"]]
                _run_trousers_case(root, target, top_product, bottom_product, case_dir, pipeline, case)
                if case["status"] == "completed":
                    try:
                        _save_case_comparison(
                            root,
                            target,
                            [("TOP SOURCE", top_product), ("TROUSERS SOURCE", bottom_product)],
                            case_dir / "result.png",
                            case_dir / "comparison.jpg",
                        )
                    except Exception as error:
                        case["comparison_error"] = str(error)
            else:
                skirt_product = products_by_id[case["bottom_id"]]
                _prepare_skirt_case(
                    root,
                    target,
                    top_product,
                    skirt_product,
                    case_dir,
                    pipeline,
                    case,
                    synthetic_tech=synthetic_tech,
                )
        except Exception as error:
            _cleanup_stage2_artifacts(case_dir, final_status="failed", reason=str(error))
            case.update(status="failed", error=str(error), traceback=traceback.format_exc())
            if error.__class__.__name__ == "OutOfMemoryError":
                summary["stopped_reason"] = "out_of_memory"
                for rest in summary["cases"][index + 1:]:
                    if rest["status"] == "pending":
                        rest["status"] = "not_run"
                _refresh_summary(root, run_dir, summary)
                raise
        finally:
            if is_single_case and summary.get("execution_mode") == SINGLE_CASE_SKIRT_MODE:
                summary["fashn_executed"] = bool(case.get("fashn_executed"))
            _refresh_summary(root, run_dir, summary)
    return summary


def _catvton_telemetry_fields(outcome):
    if not isinstance(outcome, dict):
        return {}
    fields = {}
    for src_key, dst_key in (
        ("vae_decode", "catvton_vae_decode"),
        ("peak_allocated_gib", "catvton_peak_allocated_gib"),
        ("peak_reserved_gib", "catvton_peak_reserved_gib"),
        ("error_stage", "catvton_error_stage"),
        ("error_type", "catvton_error_type"),
    ):
        value = outcome.get(src_key)
        if value is not None:
            fields[dst_key] = value
    return fields


def run_catvton_lower(root, run_dir, *, skirt_lower_fn=None, synthetic_tech=False):
    """Execute Phase 2 CatVTON skirt inference on prepared pilot cases."""
    root = Path(root).resolve()
    if skirt_lower_fn is None and not _is_current_venv(root, ".venv-catvton"):
        venv_python = _venv_python(root, ".venv-catvton")
        raise RuntimeError(
            f"CatVTON phase requires {venv_python} (active interpreter: {sys.executable})."
        )
    import local_skirt

    run_dir = _assert_pilot_run_dir(root, run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
    _assert_mode_consistency(manifest, summary, synthetic_tech=synthetic_tech)
    if summary.get("catvton_skipped") or summary.get("execution_mode") == SINGLE_CASE_FASHN_ONLY_MODE:
        raise ValueError("CatVTON phase is disabled in single-case FASHN-only mode.")
    if summary.get("single_case_mode"):
        if (
            summary.get("execution_mode") != SINGLE_CASE_SKIRT_MODE
            or len(summary.get("cases") or []) != 1
            or summary["cases"][0].get("flow_type") != "top_plus_skirt"
        ):
            raise ValueError("Run directory pilot-summary.json has an invalid single-case CatVTON configuration.")
    validated = _validate_manifest_for_mode(manifest, root, synthetic_tech=synthetic_tech)
    verify_pilot_extractions(root, validated["products"])
    targets_by_id = {t["id"]: t for t in validated["targets"]}
    products_by_id = validated["product_by_id"]

    lower_fn = skirt_lower_fn or local_skirt.lower
    original_root = local_skirt.ROOT
    local_skirt.ROOT = root
    try:
        for case in summary["cases"]:
            if case["flow_type"] != "top_plus_skirt" or case["status"] != "prepared":
                continue
            case_dir = run_dir / "cases" / case["id"]
            try:
                handoff_record = local_skirt.verify_prepared(case_dir)
                lower_fn(case_dir)
                outcome = json.loads((case_dir / "catvton-outcome.json").read_text(encoding="utf-8"))
                if (outcome.get("status") != "completed"
                        or sha256(case_dir / "02-skirt-repaint.png") != outcome.get("output_sha256")
                        or sha256(case_dir / "skirt-handoff.json") != outcome.get("handoff_sha256")):
                    raise ValueError("CatVTON skirt output verification failed.")
                result_out = local_skirt.save_final_result(case_dir, handoff_record, case_dir / "result.png")
                case.update(
                    status="completed",
                    catvton_executed=True,
                    catvton_skipped=False,
                    lower_elapsed_seconds=outcome.get("elapsed_seconds"),
                    result=result_out.relative_to(run_dir).as_posix(),
                    output_sha256=sha256(result_out),
                    **_catvton_telemetry_fields(outcome),
                )
                if summary.get("single_case_mode") and summary.get("execution_mode") == SINGLE_CASE_SKIRT_MODE:
                    summary["catvton_executed"] = True
                    summary["catvton_skipped"] = False
                    selection_path = case_dir / "selection.json"
                    if selection_path.is_file():
                        selection_data = json.loads(selection_path.read_text(encoding="utf-8"))
                        selection_data["catvton_executed"] = True
                        selection_data["catvton_skipped"] = False
                        write_json(selection_path, selection_data)
                try:
                    _save_case_comparison(
                        root,
                        targets_by_id[case["target_id"]],
                        [("TOP SOURCE", products_by_id[case["top_id"]]), ("SKIRT SOURCE", products_by_id[case["bottom_id"]])],
                        result_out,
                        case_dir / "comparison.jpg",
                    )
                except Exception as error:
                    case["comparison_error"] = str(error)
            except Exception as error:
                failed_outcome = None
                outcome_path = case_dir / "catvton-outcome.json"
                if outcome_path.is_file():
                    try:
                        failed_outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
                    except Exception:
                        failed_outcome = None
                _cleanup_stage2_artifacts(case_dir, final_status="failed", reason=str(error))
                case.update(
                    status="failed",
                    error=str(error),
                    traceback=traceback.format_exc(),
                    **_catvton_telemetry_fields(failed_outcome),
                )
                _refresh_summary(root, run_dir, summary)
                raise
            finally:
                _refresh_summary(root, run_dir, summary)
    finally:
        local_skirt.ROOT = original_root
    return summary


def run_pilot(
    root,
    manifest_path,
    *,
    include_untucked=False,
    synthetic_tech=False,
    case_id=None,
    fashn_factory=None,
    run_phase1_in_subprocess=True,
    subprocess_runner=None,
    catvton_runner=None,
):
    """Run full pilot validation (preflight, FASHN Phase 1, isolated CatVTON Phase 2)."""
    root = Path(root).resolve()
    if synthetic_tech and include_untucked:
        raise ValueError(
            "--include-untucked is only valid for the real 3x3 pilot; synthetic 2-flow pilot already defines tucked and untucked flows."
        )
    if case_id is not None and not synthetic_tech:
        raise ValueError("--case single-case mode requires --synthetic-tech.")
    manifest_file = local_path(root, manifest_path) if not Path(manifest_path).is_absolute() else Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
    _assert_mode_consistency(manifest, synthetic_tech=synthetic_tech)
    validated = _validate_manifest_for_mode(manifest, root, synthetic_tech=synthetic_tech)
    extractions = verify_pilot_extractions(root, validated["products"])
    cases = expand_pilot_cases(manifest, include_untucked=include_untucked, case_id=case_id)
    selected_single = cases[0] if case_id is not None else None
    is_single_fashn_only = bool(
        selected_single is not None and selected_single["flow_type"] == "top_only"
    )
    is_single_skirt = bool(
        selected_single is not None and selected_single["flow_type"] == "top_plus_skirt"
    )
    fashn_python = (
        _require_venv_python(root, ".venv")
        if (fashn_factory is None and run_phase1_in_subprocess)
        else None
    )

    run_dir = _create_pilot_dir(root)
    _assert_pilot_run_dir(root, run_dir)
    write_json(run_dir / "manifest.json", manifest)
    summary = {
        "schema_version": 1,
        "status": "initializing",
        "scope": (
            f"Single-case FASHN-only synthetic technical rehearsal ({selected_single['id']}); "
            "CatVTON skipped; never real-human quality or >=80% generalization evidence"
            if is_single_fashn_only
            else (
                f"Single-case FASHN + CatVTON synthetic technical rehearsal ({selected_single['id']}, tuck_top={selected_single['tuck_top']}); "
                "never real-human quality or >=80% generalization evidence"
                if is_single_skirt
                else (
                    "Synthetic 2-flow technical rehearsal only (top_only, top_plus_skirt tucked/untucked); "
                    "never real-human quality or >=80% generalization evidence"
                    if synthetic_tech
                    else "3x3 pilot readiness validation; never the >=80% general quality gate"
                )
            )
        ),
        "manifest_sha256": sha256(manifest_file),
        "include_untucked": bool(include_untucked),
        "settings": {
            "fashn": FASHN_SETTINGS,
            "catvton": (
                {"skipped": True, "reason": SINGLE_CASE_FASHN_ONLY_MODE}
                if is_single_fashn_only
                else {"steps": 50, "guidance": 2.5, "seed": 42}
            ),
        },
        "source_extractions": extractions,
        "cases": cases,
    }
    if synthetic_tech:
        is_multi = manifest.get("manifest_kind") == SYNTHETIC_MULTISUBJECT_MANIFEST_KIND
        summary.update(
            pilot_mode=SYNTHETIC_PILOT_MODE,
            manifest_kind=manifest.get("manifest_kind", SYNTHETIC_MANIFEST_KIND),
            generalization_evidence=False,
            same_base_identity=manifest.get("same_base_identity", False) if is_multi else True,
            effective_subject_diversity=3 if is_multi else 1,
            distinct_target_sha256=True,
            derived_from_base_image=manifest.get("derived_from_baseline"),
            target_sha256s={t["id"]: t["image_sha256"] for t in validated["targets"]},
            included_flows=list(manifest["included_flows"]),
            excluded_flows=list(manifest["excluded_flows"]),
            evidence_limits=(
                "Synthetic avatars represent 3 independent synthetic subjects; effective subject diversity is 3, "
                "top_plus_trousers is excluded, and generalization evidence is not established."
                if is_multi
                else (
                    "Synthetic presets all derive from avatar-baseline.png; effective subject diversity is 1 "
                    "and top_plus_trousers is excluded."
                )
            ),
        )
    if is_single_fashn_only:
        summary.update(
            single_case_mode=True,
            execution_mode=SINGLE_CASE_FASHN_ONLY_MODE,
            selected_case_id=selected_single["id"],
            selected_target_id=selected_single["target_id"],
            selected_flow_id=selected_single["flow_id"],
            selected_product_id=selected_single["top_id"],
            fashn_only=True,
            catvton_executed=False,
            catvton_skipped=True,
            catvton_skip_reason="Single-case FASHN-only mode (--case): CatVTON Phase 2 intentionally skipped.",
        )
    elif is_single_skirt:
        summary.update(
            single_case_mode=True,
            execution_mode=SINGLE_CASE_SKIRT_MODE,
            selected_case_id=selected_single["id"],
            selected_target_id=selected_single["target_id"],
            selected_flow_id=selected_single["flow_id"],
            selected_product_id=selected_single["top_id"],
            selected_bottom_id=selected_single["bottom_id"],
            tuck_top=selected_single["tuck_top"],
            fashn_only=False,
            fashn_executed=False,
            catvton_executed=False,
            catvton_skipped=False,
        )
    _refresh_summary(root, run_dir, summary)
    runner = subprocess_runner or subprocess.run

    try:
        if fashn_factory is not None or not run_phase1_in_subprocess:
            summary = run_fashn_phase(
                root,
                run_dir,
                fashn_factory=fashn_factory,
                synthetic_tech=synthetic_tech,
            )
        else:
            fashn_cmd = [
                str(fashn_python),
                "-u",
                str(Path(__file__).resolve()),
                "fashn-phase",
                "--root",
                str(root),
                "--run-dir",
                str(run_dir),
            ]
            if synthetic_tech:
                fashn_cmd.append("--synthetic-tech")
            runner(fashn_cmd, check=True, cwd=root)
            summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))

        if not is_single_fashn_only:
            prepared_skirts = [c for c in summary["cases"] if c["flow_type"] == "top_plus_skirt" and c["status"] == "prepared"]
            if prepared_skirts:
                if catvton_runner is not None:
                    catvton_runner(root, run_dir)
                else:
                    cat_python = _require_venv_python(root, ".venv-catvton")
                    cat_cmd = [
                        str(cat_python),
                        "-u",
                        str(Path(__file__).resolve()),
                        "catvton-lower",
                        "--root",
                        str(root),
                        "--run-dir",
                        str(run_dir),
                    ]
                    if synthetic_tech:
                        cat_cmd.append("--synthetic-tech")
                    runner(cat_cmd, check=True, cwd=root)
                summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        else:
            summary["catvton_executed"] = False
            summary["catvton_skipped"] = True

        for case in summary["cases"]:
            if case["status"] == "prepared":
                case["status"] = "failed"
                case.setdefault("error", "Phase 2 CatVTON stage did not complete.")
        has_failed = any(c["status"] in {"failed", "not_run"} for c in summary["cases"])
        has_blocked = any(c["status"] == "parse_blocked" for c in summary["cases"])
        summary["status"] = "failed" if has_failed else ("completed_with_parse_blocks" if has_blocked else "completed")
    except Exception as error:
        summary = json.loads((run_dir / "pilot-summary.json").read_text(encoding="utf-8"))
        for case in summary["cases"]:
            if case["status"] in {"pending", "prepared"}:
                case["status"] = "failed"
                case.setdefault("error", str(error))
        summary["status"] = "failed"
        summary["error"] = str(error)
        raise
    finally:
        _refresh_summary(root, run_dir, summary)
    return run_dir


def main(argv=None):
    cli_argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="TryFit Next 3x3 real-person pilot validation runner")
    commands = parser.add_subparsers(dest="command", required=True)

    check_p = commands.add_parser("validate", help="Validate pilot manifest and SAM2 extraction provenance without GPU")
    check_p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    check_p.add_argument("--manifest", type=Path, required=True)
    check_p.add_argument("--synthetic-tech", action="store_true")

    preflight_p = commands.add_parser("preflight", help="Validate manifest and run human-parsing preflight on real targets")
    preflight_p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    preflight_p.add_argument("--manifest", type=Path, required=True)
    preflight_p.add_argument("--synthetic-tech", action="store_true")

    run_p = commands.add_parser("run", help="Run full pilot validation (FASHN Phase 1 + isolated CatVTON Phase 2)")
    run_p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    run_p.add_argument("--manifest", type=Path, required=True)
    run_p.add_argument("--include-untucked", action="store_true")
    run_p.add_argument("--synthetic-tech", action="store_true")
    run_p.add_argument(
        "--case",
        default=None,
        help="Run only one explicit synthetic case (e.g. slender__top FASHN-only, or slender__skirt-tucked FASHN+CatVTON)",
    )

    fashn_p = commands.add_parser("fashn-phase", help=argparse.SUPPRESS)
    fashn_p.add_argument("--root", type=Path, required=True)
    fashn_p.add_argument("--run-dir", type=Path, required=True)
    fashn_p.add_argument("--synthetic-tech", action="store_true")

    cat_p = commands.add_parser("catvton-lower", help=argparse.SUPPRESS)
    cat_p.add_argument("--root", type=Path, required=True)
    cat_p.add_argument("--run-dir", type=Path, required=True)
    cat_p.add_argument("--synthetic-tech", action="store_true")

    args = parser.parse_args(cli_argv)
    if args.command == "validate":
        manifest_path = local_path(args.root, args.manifest) if not args.manifest.is_absolute() else args.manifest.resolve()
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        _assert_mode_consistency(manifest_data, synthetic_tech=args.synthetic_tech)
        validated_data = _validate_manifest_for_mode(manifest_data, args.root, synthetic_tech=args.synthetic_tech)
        verify_pilot_extractions(args.root, validated_data["products"])
        print("SYNTHETIC_PILOT_MANIFEST_VALID" if args.synthetic_tech else "PILOT_MANIFEST_VALID", flush=True)
        return 0
    if args.command == "preflight":
        try:
            _ensure_cli_venv(args.root, ".venv", cli_argv)
        except (FileNotFoundError, RuntimeError) as error:
            print(f"ERROR: {error}", file=sys.stderr, flush=True)
            return 1
        manifest_path = local_path(args.root, args.manifest) if not args.manifest.is_absolute() else args.manifest.resolve()
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        _assert_mode_consistency(manifest_data, synthetic_tech=args.synthetic_tech)
        validated_data = _validate_manifest_for_mode(manifest_data, args.root, synthetic_tech=args.synthetic_tech)
        verify_pilot_extractions(args.root, validated_data["products"])
        run_dir = _create_pilot_dir(args.root)
        _assert_pilot_run_dir(args.root, run_dir)
        write_json(run_dir / "manifest.json", manifest_data)
        from masked_outfit import MaskedOutfitPipeline
        pipeline = MaskedOutfitPipeline(args.root, validated_data["products"])
        result = run_parsing_preflight(args.root, validated_data["targets"], pipeline.hp_model, run_dir / "preflight")
        if args.synthetic_tech:
            is_multi = manifest_data.get("manifest_kind") == SYNTHETIC_MULTISUBJECT_MANIFEST_KIND
            result.update(
                pilot_mode=SYNTHETIC_PILOT_MODE,
                manifest_kind=manifest_data.get("manifest_kind", SYNTHETIC_MANIFEST_KIND),
                generalization_evidence=False,
                same_base_identity=manifest_data.get("same_base_identity", False) if is_multi else True,
                effective_subject_diversity=3 if is_multi else 1,
            )
        write_json(run_dir / "parsing-preflight.json", result)
        print(run_dir, flush=True)
        return 0
    if args.command == "run":
        try:
            dest = run_pilot(
                args.root,
                args.manifest,
                include_untucked=args.include_untucked,
                synthetic_tech=args.synthetic_tech,
                case_id=args.case,
            )
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            print(f"ERROR: {error}", file=sys.stderr, flush=True)
            return 1
        print(dest, flush=True)
        return 0
    if args.command == "fashn-phase":
        try:
            _ensure_cli_venv(args.root, ".venv", cli_argv)
        except (FileNotFoundError, RuntimeError) as error:
            print(f"ERROR: {error}", file=sys.stderr, flush=True)
            return 1
        run_fashn_phase(args.root, args.run_dir, synthetic_tech=args.synthetic_tech)
        return 0
    try:
        run_catvton_lower(args.root, args.run_dir, synthetic_tech=args.synthetic_tech)
    except (FileNotFoundError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
