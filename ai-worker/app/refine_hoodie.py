"""Bounded, recorded parameter study after the first outfit failed garment identity."""
import json
import sys
import time
import traceback
import argparse
import uuid
from pathlib import Path

import torch

from experiment import command_output, load_rgb, sha256, write_json
from outfit import create_pipeline

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--parent", type=Path, required=True, help="Original outfit run directory")
args = parser.parse_args()
PARENT = args.parent.resolve()
DEST = ROOT / "runs" / ("hoodie-refinement-" + uuid.uuid4().hex[:8])
DEST.mkdir(exist_ok=False)
person_path = PARENT / "bottom-top-1-bottoms.png"
garment_path = ROOT / "data/first-outfit/hoodie.png"
settings = [
    {"id": "guidance-2-5", "num_timesteps": 50, "seed": 42, "guidance_scale": 2.5, "segmentation_free": True},
    {"id": "seed-7", "num_timesteps": 50, "seed": 7, "guidance_scale": 2.5, "segmentation_free": True},
    {"id": "masked", "num_timesteps": 50, "seed": 42, "guidance_scale": 2.0, "segmentation_free": False},
]
record = {"status": "initializing", "quality_status": "not_reviewed", "parent_run": str(PARENT.relative_to(ROOT)),
          "person_sha256": sha256(person_path), "garment_sha256": sha256(garment_path),
          "reason": "Initial hoodie transfer changed neckline, pocket and hem.", "cases": []}
write_json(DEST / "run.json", record)
(DEST / "pip-freeze.txt").write_text(command_output([sys.executable, "-m", "pip", "freeze"])["stdout"], encoding="utf-8")
try:
    pipeline = create_pipeline(ROOT / "ai-worker/models")
    record["status"] = "running"
    for recipe in settings:
        recipe = recipe.copy()
        name = recipe.pop("id")
        item = {"id": name, "status": "running", "settings": recipe}
        record["cases"].append(item)
        write_json(DEST / "run.json", record)
        print(f"START {name}", flush=True)
        start = time.perf_counter()
        try:
            output = pipeline(person_image=load_rgb(person_path), garment_image=load_rgb(garment_path),
                              category="tops", garment_photo_type="flat-lay", num_samples=1, **recipe)
            destination = DEST / f"{name}.png"
            output.images[0].save(destination)
            item.update(status="completed", output=destination.name, output_sha256=sha256(destination))
        except Exception as error:
            item.update(status="failed", error=str(error), traceback=traceback.format_exc())
            torch.cuda.empty_cache()
        finally:
            item["elapsed_seconds"] = round(time.perf_counter()-start, 2)
            write_json(DEST / "run.json", record)
    record["status"] = "completed" if all(c["status"] == "completed" for c in record["cases"]) else "incomplete"
except Exception as error:
    record.update(status="failed", error=str(error), traceback=traceback.format_exc())
    raise
finally:
    write_json(DEST / "run.json", record)
    print(f"RUN_DIR={DEST}", flush=True)
