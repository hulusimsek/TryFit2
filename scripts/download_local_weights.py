"""Download only official model weights; use the project cache instead of user home."""
import json
import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
weights = ROOT / "ai-worker/models"


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f"Already downloaded: {destination.name}", flush=True)
        return
    partial = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as stream:
        total = 0
        next_update = 64 * 1024**2
        while chunk := response.read(4 * 1024**2):
            stream.write(chunk)
            total += len(chunk)
            if total >= next_update:
                print(f"{destination.name}: {total/1024**2:.0f} MiB", flush=True)
                next_update += 64 * 1024**2
        expected = response.headers.get("Content-Length")
        if expected and total != int(expected):
            raise IOError(f"Incomplete download: {destination.name}")
    partial.replace(destination)


provenance = {"repositories": {}, "files_sha256": {}}
for repo, files, destination in [
    ("fashn-ai/fashn-vton-1.5", ["model.safetensors"], weights),
    ("fashn-ai/DWPose", ["yolox_l.onnx", "dw-ll_ucoco_384.onnx"], weights / "dwpose"),
    ("fashn-ai/fashn-human-parser", ["config.json", "model.safetensors"], weights / "human-parser"),
]:
    revision = get_json(f"https://huggingface.co/api/models/{repo}")["sha"]
    provenance["repositories"][repo] = revision
    for filename in files:
        print(f"Downloading {repo}/{filename}", flush=True)
        path = destination / filename
        download(f"https://huggingface.co/{repo}/resolve/{revision}/{filename}", path)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024**2), b''):
                digest.update(chunk)
        provenance["files_sha256"][str(path.relative_to(weights))] = digest.hexdigest()
(ROOT / "model-provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
print("Weights downloaded", flush=True)
