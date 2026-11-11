"""Run the real ten-category manifest on the tested memory-aware local pipeline."""
import argparse
from pathlib import Path
from experiment import run_experiment, evaluate
from outfit import create_pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("evaluation/manifests/trendyol-10.actual.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = run_experiment(root, args.manifest, root / "ai-worker/models", pipeline_factory=create_pipeline)
    evaluate(result)
