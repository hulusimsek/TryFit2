"""Extract a researcher-annotated garment instance with official SAM2.1."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from experiment import load_rgb, local_path, sha256, write_json, command_output
from source_mask import choose_mask


def run(annotation, destination):
    import torch
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    root = Path(__file__).resolve().parents[2]
    spec = json.loads(Path(annotation).read_text(encoding="utf-8"))
    source = local_path(root, spec["image"])
    if sha256(source) != spec["image_sha256"]:
        raise ValueError("Annotated source changed")
    picture = load_rgb(source)
    normalized = np.asarray(spec["points_normalized"], dtype=float)
    labels = np.asarray(spec["labels"])
    if (normalized.shape != (len(labels), 2) or not np.isfinite(normalized).all()
            or (normalized < 0).any() or (normalized > 1).any() or not np.isin(labels, [0, 1]).all()
            or not (labels == 1).any() or not (labels == 0).any()):
        raise ValueError("Invalid normalized positive/negative annotation points")
    coords = np.rint(normalized * [picture.width - 1, picture.height - 1]).astype(int)
    checkpoint = root / "ai-worker/models/sam2/sam2.1_hiera_base_plus.pt"
    model = build_sam2("configs/sam2.1/sam2.1_hiera_b+.yaml", str(checkpoint), device="cuda", apply_postprocessing=False)
    predictor = SAM2ImagePredictor(model, max_hole_area=0, max_sprinkle_area=0)
    # Use float32 for the controlled extraction; VTON settings stay unchanged.
    with torch.inference_mode():
        predictor.set_image(np.array(picture))
        # Start with a coarse object proposal, then refine using all exclusions.
        first = np.flatnonzero(labels == 1)[0]
        _, initial_scores, logits = predictor.predict(point_coords=coords[first:first+1], point_labels=labels[first:first+1], multimask_output=True)
        initial = int(np.argmax(initial_scores))
        mask_input = logits[initial:initial+1]
        for _ in range(2):
            masks, scores, mask_input = predictor.predict(point_coords=coords, point_labels=labels, mask_input=mask_input, multimask_output=False)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        mask, index = choose_mask(masks, scores, coords, spec["labels"])
    except ValueError:
        write_json(destination / "rejected.json", {"annotation": spec, "scores": scores.tolist(),
            "point_pixels": coords.tolist(), "predicted_point_labels": masks[:, coords[:, 1], coords[:, 0]].astype(int).tolist()})
        for i, candidate in enumerate(masks):
            Image.fromarray(np.where(candidate[..., None], np.asarray(picture), 127).astype('uint8')).save(destination / f"rejected-{i}.png")
        raise
    Image.fromarray(mask.astype('uint8') * 255).save(destination / "mask.png")
    pixels = np.asarray(picture)
    isolated = np.where(mask[..., None], pixels, 127).astype('uint8')
    Image.fromarray(isolated).save(destination / "isolated.png")
    overlay = pixels.copy()
    overlay[mask] = (overlay[mask] * .65 + np.array([0, 220, 120]) * .35).astype('uint8')
    overlay = Image.fromarray(overlay)
    draw = ImageDraw.Draw(overlay)
    for (x, y), label in zip(coords, spec["labels"]):
        draw.ellipse((x-5, y-5, x+5, y+5), fill="lime" if label else "red", outline="black")
    overlay.save(destination / "overlay.jpg")
    write_json(destination / "extraction.json", {"annotation": spec, "annotation_sha256": sha256(annotation),
        "method": "researcher-point-prompted SAM2.1; not automatic", "candidate_scores": scores.tolist(),
        "selected_candidate": index, "foreground_fraction": float(mask.mean()), "source_size": list(picture.size),
        "mask_sha256": sha256(destination / "mask.png"), "checkpoint_sha256": sha256(checkpoint),
        "sam_commit": command_output(["git", "-C", str(root / "vendor/sam2"), "rev-parse", "HEAD"]),
        "torch": torch.__version__, "dtype": "float32", "postprocessing": False,
        "prompt_strategy": "highest-IoU single-point proposal then two full-point refinements"})
    print(destination, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("annotation", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    run(args.annotation, args.destination)
