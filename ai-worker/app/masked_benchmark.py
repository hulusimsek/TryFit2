"""Frozen-seed before/after benchmark using inspected SAM source masks."""
import argparse
import json
import math
from contextlib import nullcontext
from pathlib import Path
import numpy as np
from PIL import Image
from experiment import run_experiment, evaluate, sha256, write_json
from outfit import create_pipeline
from source_mask import SourceMaskParser, SourcePoseAblation


def run(ids, extraction_dirs, *, disable_source_pose=False, steps=30, guidance=1.5):
    if steps < 1 or not math.isfinite(guidance) or guidance <= 0:
        raise ValueError("Positive steps and finite positive guidance required")
    root = Path(__file__).resolve().parents[2]
    manifest = root / "evaluation/manifests/trendyol-10.actual.json"
    cases = json.loads(manifest.read_text(encoding="utf-8"))["cases"]
    entries = {}
    for case_id, directory in zip(ids, extraction_dirs, strict=True):
        directory = Path(directory).resolve()
        meta = json.loads((directory / "extraction.json").read_text(encoding="utf-8"))
        case = next(c for c in cases if c["id"] == case_id)
        if (meta["annotation"]["image_sha256"] != case["image_sha256"]
                or sha256(root / case["image"]) != case["image_sha256"]
                or meta["annotation"]["id"] != case_id
                or meta["annotation"]["category"] != case["category"]
                or sha256(directory / "mask.png") != meta["mask_sha256"]):
            raise ValueError("Mask/source provenance mismatch")
        entries[sha256(root / case["image"])] = (case, directory, meta)

    class MaskedPipeline:
        def __init__(self, weights):
            self.pipeline = create_pipeline(weights, parser_factory=SourceMaskParser)
            self.inference_dtype = self.pipeline.inference_dtype
            if disable_source_pose:
                from fashn_vton.utils import get_dummy_dw_keypoints
                self.pipeline.pose_model = SourcePoseAblation(self.pipeline.pose_model, get_dummy_dw_keypoints)

        def __call__(self, **kwargs):
            # Match RGB bytes to the frozen source; no previous-case mask reuse.
            from experiment import load_rgb
            matching = [(case, directory, meta) for case, directory, meta in entries.values()
                        if load_rgb(root / case["image"]).tobytes() == kwargs["garment_image"].tobytes()
                        and load_rgb(root / case["image"]).size == kwargs["garment_image"].size]
            if len(matching) != 1:
                raise ValueError("Ambiguous or missing source mask")
            case, directory, meta = matching[0]
            if case["category"] != kwargs["category"]:
                raise ValueError("Mask category mismatch")
            mask = np.asarray(Image.open(directory / "mask.png").convert("L"))
            pose_context = self.pipeline.pose_model.use() if disable_source_pose else nullcontext()
            with pose_context, self.pipeline.hp_model.use(mask, kwargs["category"], kwargs["garment_image"].size,
                                           segmentation_free=kwargs["segmentation_free"],
                                           garment_photo_type=kwargs["garment_photo_type"]):
                return self.pipeline(**kwargs)

    result = run_experiment(root, manifest, root / "ai-worker/models", selected_ids=ids,
                            steps=steps, guidance=guidance, pipeline_factory=MaskedPipeline)
    write_json(result / "source-mask-provenance.json", {
        "baseline": "runs/20261110T003636Z-688ebfd6",
        "masked_baseline": "runs/20261110T095148Z-cf9135a6",
        "controlled_changes": ["researcher-point-prompted source garment mask"] + (["empty source pose; original model-photo preprocessing retained"] if disable_source_pose else [])
            + ([f"steps={steps}; guidance={guidance}"] if steps != 30 or guidance != 1.5 else []),
        "unchanged": ["source photo", "target pose", "target", "category", "seed42"] + ([] if disable_source_pose else ["source pose"]),
        "note": "Pinned FASHN has no separate photo-type embedding; photo type controls source masking and pose preprocessing.",
        "extractions": {case["id"]: {"directory": str(directory.relative_to(root)), "metadata": meta}
                        for case, directory, meta in entries.values()}})
    evaluate(result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", required=True)
    parser.add_argument("--extraction", action="append", type=Path, required=True)
    parser.add_argument("--disable-source-pose", action="store_true")
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance", type=float, default=1.5)
    args = parser.parse_args()
    run(args.case, args.extraction, disable_source_pose=args.disable_source_pose, steps=args.steps, guidance=args.guidance)
