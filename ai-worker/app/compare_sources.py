"""Compare real product gallery sources under identical inference settings."""
import argparse
import json
import time
import traceback
import uuid
from pathlib import Path

from experiment import load_rgb, sha256, write_json
from outfit import create_pipeline


def run(parent):
    root = Path(__file__).resolve().parents[2]
    parent = Path(parent).resolve()
    target = parent / "bottom-top-1-bottoms.png"
    gallery = root / "data/first-outfit/gallery"
    sources = json.loads((gallery / "sources.json").read_text(encoding="utf-8"))
    destination = root / "runs" / ("source-comparison-" + uuid.uuid4().hex[:8])
    destination.mkdir()
    settings = dict(seed=42, num_timesteps=30, guidance_scale=1.5, segmentation_free=True, num_samples=1)
    record = {"status": "initializing", "quality_status": "not_reviewed", "settings": settings,
              "parent_run": str(parent.relative_to(root)), "person_sha256": sha256(target), "cases": []}
    write_json(destination / "run.json", record)
    try:
        pipeline = create_pipeline(root / "ai-worker/models")
        record["status"] = "running"
        for name, filename, kind in [("worn-raised-arm", "gallery-4.jpg", "model"),
                                     ("worn-seated", "gallery-3.jpg", "model"),
                                     ("clean-flat-lay", "gallery-1.jpg", "flat-lay")]:
            source = gallery / filename
            source_metadata = next(s for s in sources if Path(s["image"]).name == filename)
            case = {"id": name, "source": source_metadata, "source_sha256": sha256(source),
                    "garment_photo_type": kind, "status": "running"}
            record["cases"].append(case)
            write_json(destination / "run.json", record)
            print(f"START {name}", flush=True)
            start = time.perf_counter()
            try:
                output = pipeline(person_image=load_rgb(target), garment_image=load_rgb(source),
                                  category="tops", garment_photo_type=kind, **settings)
                path = destination / f"{name}.png"
                output.images[0].save(path)
                case.update(status="completed", output=path.name, output_sha256=sha256(path))
            except Exception as error:
                case.update(status="failed", error=str(error), traceback=traceback.format_exc())
                raise
            finally:
                case["elapsed_seconds"] = round(time.perf_counter()-start, 2)
                write_json(destination / "run.json", record)
        record["status"] = "completed"
    except Exception as error:
        record.update(status="failed", error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        write_json(destination / "run.json", record)
        print(f"RUN_DIR={destination}", flush=True)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, required=True)
    run(parser.parse_args().parent)
