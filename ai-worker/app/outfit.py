"""Sequential two-piece VTON experiment with CPU preprocessing for an 8 GB GPU.

The synthetic avatar is a visual proxy, never a measured body reconstruction.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from experiment import command_output, load_rgb, local_path, sha256, write_json


def validate_selection(selection, root):
    avatar = selection["avatar"]
    for key in ("height_cm", "weight_kg"):
        value = avatar[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Invalid avatar {key}")
    if not local_path(root, avatar["image"]).is_file():
        raise ValueError("Avatar image missing")
    items = selection["items"]
    if len(items) != 2 or {item["category"] for item in items} != {"tops", "bottoms"}:
        raise ValueError("First outfit requires exactly one top and one bottom")
    for item in items:
        if item["garment_photo_type"] not in {"model", "flat-lay"}:
            raise ValueError("Invalid garment photo type")
        if sha256(local_path(root, item["image"])) != item["image_sha256"]:
            raise ValueError(f"Source image hash changed: {item['id']}")
    return items


def sequential_cfg(model, *args, **kwargs):
    import torch
    # Same masks and branch outputs as upstream, without a doubled batch.
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    x = args[0]
    mask = torch.ones(x.shape[0], device=x.device, dtype=torch.bool)
    conditional = model.forward(*args, **kwargs, mask=mask)["x"]
    unconditional = model.forward(*args, **kwargs, mask=~mask)["x"]
    return {"v_c": conditional, "v_u": unconditional}


def create_pipeline(weights, *, parser_factory=None):
    """Keep upstream inference math; execute the two CFG branches sequentially."""
    import types
    import torch
    from fashn_vton import TryOnPipeline
    from fashn_vton.dwpose import DWposeDetector
    from fashn_human_parser import FashnHumanParser
    from fashn_vton.tryon_mmdit import TryOnModel
    from fashn_vton.utils import load_checkpoint
    from upper_preservation import UpperPreservingPipelineMixin

    class MemoryAwarePipeline(UpperPreservingPipelineMixin, TryOnPipeline):
        def _setup_tryon_model(self):
            model = TryOnModel()
            state = load_checkpoint(str(Path(self.weights_dir) / "model.safetensors"), device="cpu")
            model.load_state_dict(state)
            del state
            self.tryon_model = model.to(self.device, dtype=self.inference_dtype).eval()

        def _setup_pose_model(self):
            self.pose_model = DWposeDetector(checkpoints_dir=str(Path(self.weights_dir) / "dwpose"), device="cpu")

        def _setup_hp_model(self):
            self.hp_model = FashnHumanParser(model_id=str(Path(self.weights_dir) / "human-parser"), device="cpu")
            if parser_factory is not None:
                self.hp_model = parser_factory(self.hp_model)

    pipeline = MemoryAwarePipeline(weights_dir=str(weights), device="cuda")
    pipeline.tryon_model.forward_for_cfg = types.MethodType(sequential_cfg, pipeline.tryon_model)
    return pipeline


def save_board(run_dir, avatar, items, root, results):
    from PIL import Image, ImageDraw, ImageOps
    pictures = [("SYNTHETIC BASE", avatar)]
    pictures.extend((item["category"].upper() + " SOURCE", load_rgb(local_path(root, item["image"]))) for item in items)
    pictures.extend((order.upper(), load_rgb(path)) for order, path in results.items())
    width = len(pictures) * 320
    board = Image.new("RGB", (width, 520), "#f5f5f5")
    draw = ImageDraw.Draw(board)
    for i, (label, picture) in enumerate(pictures):
        image = ImageOps.contain(picture, (312, 480))
        board.paste(image, (i * 320 + (320-image.width)//2, 30 + (480-image.height)//2))
        draw.text((i*320+8, 8), label, fill="#111111")
    board.save(run_dir / "comparison.jpg")


def run(root, selection_path, *, orders=("bottom-top", "top-bottom"), steps=30):
    root = Path(root).resolve()
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    items = validate_selection(selection, root)
    avatar = load_rgb(local_path(root, selection["avatar"]["image"]))
    run_dir = root / "runs" / ("outfit-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])
    run_dir.mkdir(parents=True)
    weights = root / "ai-worker/models"
    record = {
        "status": "initializing", "quality_status": "not_reviewed", "stages": [],
        "avatar": selection["avatar"], "avatar_sha256": sha256(local_path(root, selection["avatar"]["image"])),
        "settings": {"seed": 42, "num_timesteps": steps, "num_samples": 1, "guidance_scale": 1.5, "segmentation_free": True},
        "adaptations": ["CPU pose and human parsing", "CPU checkpoint load", "sequential CFG branches"],
        "selection_sha256": sha256(selection_path),
    }
    write_json(run_dir / "selection.json", selection)
    write_json(run_dir / "run.json", record)
    results = {}
    try:
        import torch
        import onnxruntime as ort
        record["environment"] = {"python": sys.version, "torch": torch.__version__, "cuda": torch.version.cuda,
                                 "onnxruntime": ort.__version__, "pose_provider": "CPUExecutionProvider"}
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable")
        record["environment"].update(gpu=torch.cuda.get_device_name(0), bf16=torch.cuda.is_bf16_supported())
        record["upstream_commit"] = command_output(["git", "-C", str(root/"vendor/fashn-vton-1.5"), "rev-parse", "HEAD"])
        (run_dir / "pip-freeze.txt").write_text(command_output([sys.executable, "-m", "pip", "freeze"])["stdout"], encoding="utf-8")
        record["weight_sha256"] = {str(p.relative_to(weights)): sha256(p) for p in sorted(weights.rglob("*")) if p.suffix in {".safetensors", ".onnx"}}
        provenance = root / "model-provenance.json"
        if provenance.exists():
            record["model_provenance"] = json.loads(provenance.read_text(encoding="utf-8"))
        pipeline = create_pipeline(weights)
        record.update(status="running", actual_dtype=str(pipeline.inference_dtype))
        for order in orders:
            categories = ["bottoms", "tops"] if order == "bottom-top" else ["tops", "bottoms"]
            person = avatar.copy()
            for index, category in enumerate(categories):
                item = next(item for item in items if item["category"] == category)
                stage = {"order": order, "index": index+1, "item": item["id"], "status": "running",
                         "person_input": "avatar" if index == 0 else record["stages"][-1]["output"],
                         "garment_photo_type": item["garment_photo_type"]}
                record["stages"].append(stage)
                write_json(run_dir / "run.json", record)
                print(f"START {order} {category}", flush=True)
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
                start = time.perf_counter()
                try:
                    output = pipeline(person_image=person, garment_image=load_rgb(local_path(root, item["image"])),
                                      category=category, garment_photo_type=item["garment_photo_type"], **record["settings"])
                    torch.cuda.synchronize()
                    person = output.images[0]
                    destination = run_dir / f"{order}-{index+1}-{category}.png"
                    person.save(destination)
                    stage.update(status="completed", output=destination.name, output_sha256=sha256(destination),
                                 peak_allocated_gib=round(torch.cuda.max_memory_allocated()/2**30, 3),
                                 peak_reserved_gib=round(torch.cuda.max_memory_reserved()/2**30, 3))
                except Exception as error:
                    stage.update(status="failed", error=str(error), error_type=type(error).__name__)
                    raise
                finally:
                    stage["elapsed_seconds"] = round(time.perf_counter()-start, 2)
                    write_json(run_dir / "run.json", record)
            results[order] = destination
            save_board(run_dir, avatar, items, root, results)
        record["status"] = "completed"
    except Exception as error:
        record.update(status="failed", error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        record["results"] = {k: v.name for k, v in results.items()}
        write_json(run_dir / "run.json", record)
        print(f"RUN_DIR={run_dir}", flush=True)
    return run_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--selection", type=Path, default=Path("evaluation/manifests/first-outfit.selection.json"))
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--order", choices=["both", "bottom-top", "top-bottom"], default="both")
    args = parser.parse_args()
    run(args.root, args.selection, orders=("bottom-top", "top-bottom") if args.order == "both" else (args.order,), steps=args.steps)
