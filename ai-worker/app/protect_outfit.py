"""Test upper-first inference with explicit semantic preservation during bottom swap."""
import json
import time
import traceback
import uuid
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from experiment import load_rgb, sha256, write_json
from outfit import create_pipeline, validate_selection


def protect_upper(first, second, labels):
    if first.size != second.size or labels.shape != (first.height, first.width):
        raise ValueError("Images and semantic mask must share the same geometry")
    # Parser labels: face, hair, top, arms, hands. Keep the generated first top
    # and identity; the second model supplies pants, feet and surrounding pixels.
    binary = np.isin(labels, [1, 2, 3, 12, 13]).astype(np.uint8) * 255
    alpha = cv2.GaussianBlur(binary, (3, 3), 0).astype(np.float32) / 255
    a = np.asarray(first).astype(np.float32)
    b = np.asarray(second).astype(np.float32)
    result = np.rint(a * alpha[..., None] + b * (1-alpha[..., None])).clip(0, 255).astype(np.uint8)
    return Image.fromarray(result), Image.fromarray(binary)


def preservation_metrics(first, second, result, binary):
    a, b, c = (np.asarray(image).astype(np.int16) for image in (first, second, result))
    m = np.asarray(binary)
    core = cv2.erode(m, np.ones((3, 3), np.uint8)) == 255
    outside = cv2.dilate(m, np.ones((3, 3), np.uint8)) == 0
    metrics = {
        "protected_interior_pixels": int(core.sum()),
        "protected_max_channel_error": int(np.abs(a-c)[core].max()) if core.any() else None,
        "unprotected_pixels": int(outside.sum()),
        "unprotected_max_channel_error": int(np.abs(b-c)[outside].max()) if outside.any() else None,
    }
    if metrics["protected_max_channel_error"] != 0 or metrics["unprotected_max_channel_error"] != 0:
        raise ValueError("Preservation invariant failed or mask has no usable interior/exterior")
    return metrics


def run(selection_path=None, *, pipeline=None, extra_metadata=None, bottom_segmentation_free=True):
    root = Path(__file__).resolve().parents[2]
    selection_path = Path(selection_path or root / "evaluation/manifests/first-outfit.protected.json")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    items = validate_selection(selection, root)
    upper = next(item for item in items if item["category"] == "tops")
    lower = next(item for item in items if item["category"] == "bottoms")
    dest = root / "runs" / ("protected-outfit-" + uuid.uuid4().hex[:8])
    dest.mkdir()
    target = root / selection["avatar"]["image"]
    upper_path, lower_path = (root / item["image"] for item in (upper, lower))
    settings = dict(num_timesteps=30, seed=42, guidance_scale=1.5, segmentation_free=True, num_samples=1)
    bottom_settings = {**settings, "segmentation_free": bottom_segmentation_free}
    record = {"status": "initializing", "quality_status": "not_reviewed", "settings": settings,
              "steps": [], "input_sha256": {name: sha256(p) for name, p in [("avatar", target), ("tops", upper_path), ("bottoms", lower_path)]},
              "selection_sha256": sha256(selection_path), "avatar_profile": selection["avatar"],
              "method": "VTON top first, VTON bottom second, semantic preservation of top/face/hair/arms/hands with 3x3 edge feather"}
    record["stage_settings"] = {"top": settings, "bottom": bottom_settings}
    if extra_metadata is not None:
        record["experiment_metadata"] = extra_metadata
    write_json(dest / "selection.json", selection)
    write_json(dest / "run.json", record)
    try:
        pipeline = pipeline or create_pipeline(root / "ai-worker/models")
        record["status"] = "running"
        start = time.perf_counter()
        top = pipeline(person_image=load_rgb(target), garment_image=load_rgb(upper_path), category="tops", garment_photo_type=upper["garment_photo_type"], **settings).images[0]
        top.save(dest / "01-top.png")
        record["steps"].append({"stage": "top", "elapsed_seconds": round(time.perf_counter()-start, 2), "output": "01-top.png"})
        write_json(dest / "run.json", record)
        print("TOP_COMPLETED", flush=True)
        start = time.perf_counter()
        raw = pipeline(person_image=top, garment_image=load_rgb(lower_path), category="bottoms", garment_photo_type=lower["garment_photo_type"], **bottom_settings).images[0]
        raw.save(dest / "02-bottom-raw.png")
        record["steps"].append({"stage": "bottom", "elapsed_seconds": round(time.perf_counter()-start, 2), "output": "02-bottom-raw.png"})
        write_json(dest / "run.json", record)
        labels = pipeline.hp_model.predict(np.asarray(top))
        if not np.any(labels == 3):
            raise ValueError("Human parser found no upper garment to preserve")
        result, mask = protect_upper(top, raw, labels)
        result.save(dest / "03-protected-outfit.png")
        mask.save(dest / "upper-protection-mask.png")
        record["preservation_checks"] = preservation_metrics(top, raw, result, mask)
        record.update(status="completed", output_sha256=sha256(dest / "03-protected-outfit.png"))
    except Exception as error:
        record.update(status="failed", error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        write_json(dest / "run.json", record)
        print(f"RUN_DIR={dest}", flush=True)
    return dest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path)
    run(parser.parse_args().selection)
