"""Three independently configured outfit tests; shared model, fresh target per pair."""
import json
from pathlib import Path
from outfit import create_pipeline
from protect_outfit import run
from experiment import write_json


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    pipeline = create_pipeline(root / "ai-worker/models")
    results = []
    for name in ("tshirt-trousers", "blouse-skirt", "denim-trousers"):
        path = root / "evaluation/manifests" / (name + ".outfit.json")
        print(f"OUTFIT_START={name}", flush=True)
        output = run(path, pipeline=pipeline)
        results.append({"name": name, "manifest": path.relative_to(root).as_posix(), "run_dir": output.relative_to(root).as_posix()})
        write_json(root / "runs/latest-outfit-suite.json", results)
