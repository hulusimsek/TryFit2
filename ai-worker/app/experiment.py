"""Local, sequential research experiments. No remote inference or fallback images."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import platform
import re
import subprocess
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

METRICS = ("garment_identity", "color_pattern", "cut", "face", "body", "arms_hands", "fabric", "source_pose")
CATEGORIES = {"tops", "bottoms", "one-pieces"}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_path(root, name):
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Girdi yolu proje klasörünün dışında olamaz.")
    return path


def validate_manifest(manifest, root, selected_ids=None):
    if manifest.get("schema_version") != 1:
        raise ValueError("Desteklenmeyen manifest sürümü.")
    person = manifest.get("person", {})
    if person.get("consent_confirmed") is not True:
        raise ValueError("Hedef fotoğraf için kullanım izni doğrulanmalı.")
    if not local_path(root, person["image"]).is_file():
        raise ValueError("Hedef kişi fotoğrafı bulunamadı.")
    cases = manifest.get("cases", [])
    ids = [case.get("id", "") for case in cases]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[a-z0-9-]+", i) for i in ids):
        raise ValueError("Deney kimlikleri benzersiz ve küçük harf/rakam/tire içermeli.")
    if selected_ids and not set(selected_ids).issubset(ids):
        raise ValueError("Seçilen deney kimliği manifestte yok.")
    selected = [c for c in cases if not selected_ids or c["id"] in selected_ids]
    if not selected:
        raise ValueError("En az bir deney gerekli.")
    for case in selected:
        url = urlparse(case.get("product_url", ""))
        host = (url.hostname or "").lower()
        if url.scheme != "https" or not (host == "trendyol.com" or host.endswith(".trendyol.com")) or "-p-" not in url.path:
            raise ValueError(f'{case["id"]}: gerçek Trendyol ürün URL’si gerekli.')
        if case.get("category") not in CATEGORIES or case.get("garment_photo_type") not in {"model", "flat-lay"}:
            raise ValueError(f'{case["id"]}: kategori veya mankenli görsel türü geçersiz.')
        if not case.get("source_image_url") or not case.get("source_notes"):
            raise ValueError(f'{case["id"]}: kaynak görsel URL’si ve poz notu gerekli.')
        if not local_path(root, case["image"]).is_file():
            raise ValueError(f'{case["id"]}: ürün görseli bulunamadı.')
    return selected


def command_output(args):
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def preflight():
    import torch
    import onnxruntime as ort
    info = {
        "python": platform.python_version(), "platform": platform.platform(),
        "torch": torch.__version__, "torch_cuda": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(), "onnxruntime": ort.__version__,
        "onnx_providers": ort.get_available_providers(),
    }
    if info["cuda_available"]:
        info.update(gpu=torch.cuda.get_device_name(0),
                    vram_gib=round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2),
                    bf16_supported=torch.cuda.is_bf16_supported())
        info["expected_dtype"] = "bfloat16" if info["bf16_supported"] else "float32"
    return info


def load_rgb(path):
    from PIL import Image, ImageOps
    with Image.open(path) as original:
        return ImageOps.exif_transpose(original).convert("RGB")


def make_comparison(person, garment, output, destination):
    from PIL import Image, ImageDraw, ImageOps
    board = Image.new("RGB", (960, 512), "#f3f4f6")
    draw = ImageDraw.Draw(board)
    for index, (title, picture) in enumerate((("SOURCE GARMENT", garment), ("TARGET PERSON", person), ("GENERATED", output))):
        thumb = ImageOps.contain(picture, (312, 476))
        board.paste(thumb, (index * 320 + (320 - thumb.width) // 2, 28 + (476 - thumb.height) // 2))
        draw.text((index * 320 + 8, 8), title, fill="black")
    board.save(destination)


def run_experiment(root, manifest_path, weights_dir, selected_ids=None, *, seed=42, steps=30,
                   guidance=1.5, segmentation_free=True, pipeline_factory=None):
    """Raises on invalid inputs/setup; preserves individual inference failures in run.json."""
    root = Path(root).resolve()
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    cases = validate_manifest(manifest, root, selected_ids)
    # Decode every selected image before reserving a GPU pipeline.
    person = load_rgb(local_path(root, manifest["person"]["image"]))
    for case in cases:
        load_rgb(local_path(root, case["image"]))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / "runs" / f"{stamp}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True)
    record = {"schema_version": 1, "created_at": stamp, "status": "initializing", "cases": [],
              "quality_status": "not_reviewed", "settings": {
                  "seed": seed, "num_timesteps": steps, "guidance_scale": guidance,
                  "segmentation_free": segmentation_free, "num_samples": 1},
              "manifest_sha256": sha256(manifest_path),
              "person_sha256": sha256(local_path(root, manifest["person"]["image"]))}
    write_json(run_dir / "manifest.json", manifest)
    write_json(run_dir / "run.json", record)
    try:
        record["environment"] = preflight()
        (run_dir / "pip-freeze.txt").write_text(command_output([__import__("sys").executable, "-m", "pip", "freeze"])["stdout"], encoding="utf-8")
        record["upstream_commit"] = command_output(["git", "-C", str(root / "vendor/fashn-vton-1.5"), "rev-parse", "HEAD"])
        if not record["environment"]["cuda_available"]:
            raise RuntimeError("CUDA GPU yok; CPU üretimi başlatılmadı.")
        if "CUDAExecutionProvider" not in record["environment"]["onnx_providers"]:
            raise RuntimeError("ONNX CUDA provider yok; CUDA/cuDNN kurulumunu kontrol edin.")
        weight_files = sorted(Path(weights_dir).rglob("*.safetensors")) + sorted(Path(weights_dir).rglob("*.onnx"))
        record["weight_sha256"] = {str(p.relative_to(weights_dir)): sha256(p) for p in weight_files}
        provenance = root / "model-provenance.json"
        if provenance.exists():
            record["model_provenance"] = json.loads(provenance.read_text(encoding="utf-8"))
        write_json(run_dir / "run.json", record)
        import torch
        if pipeline_factory is None:
            from fashn_vton import TryOnPipeline
            pipeline = TryOnPipeline(weights_dir=str(weights_dir), device="cuda")
        else:
            pipeline = pipeline_factory(weights_dir)
            record["pipeline_factory"] = pipeline_factory.__module__ + "." + pipeline_factory.__name__
        record["actual_dtype"] = str(pipeline.inference_dtype)
        record["status"] = "running"
        for case in cases:
            item = {"id": case["id"], "status": "running", "quality_status": "not_reviewed",
                    "garment_sha256": sha256(local_path(root, case["image"]))}
            record["cases"].append(item)
            write_json(run_dir / "run.json", record)
            start = time.perf_counter()
            try:
                garment = load_rgb(local_path(root, case["image"]))
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
                output = pipeline(person_image=person, garment_image=garment,
                                  category=case["category"], garment_photo_type=case["garment_photo_type"], **record["settings"])
                torch.cuda.synchronize()
                if not output.images:
                    raise RuntimeError("Model boş çıktı döndürdü.")
                destination = run_dir / f'{case["id"]}.png'
                output.images[0].save(destination)
                item.update(status="completed", output=destination.name, output_sha256=sha256(destination),
                            peak_allocated_gib=round(torch.cuda.max_memory_allocated() / 2**30, 3),
                            peak_reserved_gib=round(torch.cuda.max_memory_reserved() / 2**30, 3))
                # Presentation failure cannot erase the existence of a real inference output.
                try:
                    make_comparison(person, garment, output.images[0], run_dir / f'{case["id"]}-comparison.jpg')
                except Exception as error:
                    item["comparison_error"] = str(error)
            except Exception as error:
                item.update(status="failed", error_type=type(error).__name__, error=str(error),
                            traceback=traceback.format_exc())
                torch.cuda.empty_cache()
                if isinstance(error, torch.cuda.OutOfMemoryError):
                    record["stopped_reason"] = "out_of_memory"
            finally:
                item["elapsed_seconds"] = round(time.perf_counter() - start, 3)
                write_json(run_dir / "run.json", record)
            if record.get("stopped_reason"):
                break
        attempted = {c["id"] for c in record["cases"]}
        record["cases"].extend({"id": c["id"], "status": "not_run", "quality_status": "not_reviewed"}
                               for c in cases if c["id"] not in attempted)
        record["status"] = "completed" if all(c["status"] == "completed" for c in record["cases"]) else "incomplete"
    except Exception as error:
        record.update(status="setup_failed", error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        write_json(run_dir / "run.json", record)
        create_review(run_dir, record)
        print(f"Deney kaydı: {run_dir}")
    return run_dir


def create_review(run_dir, record):
    """Blank scores always stay blank; generation is never a quality pass."""
    path = Path(run_dir) / "review.csv"
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "reviewer", *METRICS, "untargeted_changes", "critical_failure", "notes"])
        writer.writeheader()
        writer.writerows({"id": c["id"]} for c in record["cases"])


def evaluate(run_dir):
    run_dir = Path(run_dir)
    record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    with (run_dir / "review.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    reviews = {}
    for row in rows:
        if row["id"] in reviews:
            raise ValueError("Aynı deney için birden fazla değerlendirme satırı var.")
        reviews[row["id"]] = row
    decisions = []
    for case in record["cases"]:
        row = reviews.get(case["id"], {})
        decision = "not_reviewed"
        if case["status"] != "completed":
            decision = "not_generated"
        elif row.get("critical_failure", "").strip().lower() == "yes" or row.get("untargeted_changes", "no").strip().lower() == "yes":
            decision = "failed"
        elif row.get("reviewer", "").strip() and row.get("critical_failure", "").strip().lower() == "no" and row.get("untargeted_changes", "no").strip().lower() == "no":
            raw = [row.get(metric, "").strip() for metric in METRICS]
            if all(value in {"0", "1", "2", "3", "4"} for value in raw):
                decision = "passed" if min(map(int, raw)) >= 3 else "failed"
        decisions.append({"id": case["id"], "decision": decision, "review": row})
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    expected = {c["id"] for c in manifest["cases"]}
    complete_suite = len(expected) == 10 and {c["id"] for c in record["cases"]} == expected
    passed = sum(d["decision"] == "passed" for d in decisions)
    pending = any(d["decision"] == "not_reviewed" for d in decisions)
    gate = "pending" if pending or not complete_suite else ("passed" if passed >= 8 else "failed")
    summary = {"quality_gate": gate, "passed": passed, "expected": 10,
               "complete_suite": complete_suite, "decisions": decisions,
               "scope": "Tek hedef kişi; genel kullanıcı başarısı veya beden uyumu kanıtı değildir."}
    write_json(run_dir / "quality.json", summary)
    sections = ["<!doctype html><html lang='tr'><meta charset='utf-8'><title>TryFit Next deney raporu</title>",
                "<style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:16px}img{max-width:100%}pre{white-space:pre-wrap}</style>",
                "<h1>TryFit Next — insan değerlendirmesi</h1>",
                f"<p>Kalite eşiği: {gate}. Geçen: {passed}/10.</p>"]
    for item in decisions:
        identifier = item["id"]
        sections.append(f"<h2>{html.escape(identifier)}: {item['decision']}</h2>")
        comparison = run_dir / f"{identifier}-comparison.jpg"
        if comparison.exists():
            sections.append(f'<img src="{html.escape(comparison.name, quote=True)}" alt="Kaynak, hedef, sonuç">')
        sections.append("<pre>" + html.escape(json.dumps(item["review"], ensure_ascii=False, indent=2)) + "</pre>")
    sections.append("</html>")
    (run_dir / "report.html").write_text("\n".join(sections), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TryFit Next araştırma araçları")
    commands = parser.add_subparsers(dest="command", required=True)
    review_parser = commands.add_parser("evaluate", help="Doldurulmuş review.csv dosyasını değerlendir")
    review_parser.add_argument("run_dir", type=Path)
    run_parser = commands.add_parser("run", help="CUDA ortamında gerçek inference")
    run_parser.add_argument("--root", type=Path, required=True)
    run_parser.add_argument("--manifest", type=Path, required=True)
    run_parser.add_argument("--weights", type=Path, required=True)
    run_parser.add_argument("--case", action="append", dest="cases")
    args = parser.parse_args()
    if args.command == "evaluate":
        print(json.dumps(evaluate(args.run_dir), ensure_ascii=False, indent=2))
    else:
        run_experiment(args.root, args.manifest, args.weights, selected_ids=args.cases)
