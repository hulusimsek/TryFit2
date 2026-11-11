"""Package reviewed real inference outputs into a portable, offline research report."""
import argparse
import html
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def escape(value):
    return html.escape(str(value), quote=True)


def build(run_dir, probe_dir=None):
    run_dir = Path(run_dir).resolve()
    record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    quality = json.loads((run_dir / "quality.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in manifest["cases"]}
    scores = {c["id"]: c for c in quality["decisions"]}
    destination = ROOT / "dist/validation-10"
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    def asset(source, name):
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, assets / name)
        return "assets/" + name

    def image(source, name, caption):
        uri = asset(source, name)
        return f'<figure><a href="{escape(uri)}"><img loading="lazy" src="{escape(uri)}" alt="{escape(caption)}"></a><figcaption>{escape(caption)}</figcaption></figure>'

    body = ['<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TryFit Next — Gerçek kalite deneyi</title>',
        '<style>body{font:16px/1.5 system-ui,sans-serif;max-width:1200px;margin:0 auto;padding:28px;background:#f6f5f1;color:#202320}h1{font-size:32px}article{background:white;padding:22px;margin:24px 0;border-radius:12px}.pictures{display:flex;gap:12px;flex-wrap:wrap}figure{margin:0;flex:1;min-width:180px;max-width:380px}img{width:100%;height:440px;object-fit:contain;background:#f1f1f1}figcaption{font-size:14px;color:#555}table{border-collapse:collapse;font-size:14px}td,th{padding:8px;border:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere}.pass{color:#126b3b}.fail{color:#a02722}a{color:#285652}summary{cursor:pointer}</style>',
        '<h1>TryFit Next · 10 ürünlük gerçek deney</h1>',
        f'<p><strong>Görsel ön değerlendirme: {quality["passed"]}/10.</strong> Araştırma eşiği: en az 8/10. Sonuç: <strong>{escape(quality["quality_gate"])}</strong>.</p>',
        '<p>Tek sentetik hedef kişi ve sabit seed 42 / 30 adım / guidance 1.5. 175 cm / 65 kg görsel bir profildir; ölçülü vücut veya gerçek beden uyumu kanıtı değildir. Puanlar asistanın görsel ön incelemesidir, bağımsız insan paneli veya otomatik doğruluk ölçümü değildir.</p>',
        '<p>On gerçek Trendyol ürün kaydındaki giyilmiş kıyafet görselleri kullanıldı. Geniş pantolon kaynağında AI üretim etiketi gözlendi. Ham model sonuçları aşağıda; koruma maskeli kombinler ayrı bölümde. Sekiz görsel puana ek olarak seçilmemiş kıyafet/aksesuar değişimi başarısızlık koşuludur; bu kontrol vücut şekli puanından ayrıdır.</p>',
        '<p><a href="assets/review.csv">Puan CSV</a> · <a href="assets/manifest.json">Ürün ve kaynak kayıtları</a> · <a href="assets/run.json">Çalıştırma kaydı</a></p>']
    for name in ("review.csv", "manifest.json", "run.json", "quality.json", "pip-freeze.txt"):
        asset(run_dir / name, name)
    asset(ROOT / manifest["person"]["image"], "target.png")
    metrics = [("garment_identity", "Ürün"), ("color_pattern", "Renk/desen"), ("cut", "Kesim"), ("face", "Yüz"),
               ("body", "Vücut/koruma"), ("arms_hands", "Kol/el"), ("fabric", "Kumaş"), ("source_pose", "Kaynak poz")]
    for case_record in record["cases"]:
        identifier = case_record["id"]
        case, score = cases[identifier], scores[identifier]
        review = score["review"]
        state = "pass" if score["decision"] == "passed" else "fail"
        body.append(f'<article><h2>{escape(case["label"])} · <span class="{state}">{escape(score["decision"])}</span></h2><div class="pictures">')
        body.append(image(ROOT / case["image"], identifier + "-source" + Path(case["image"]).suffix, "Kaynak ürün"))
        body.append('<figure><a href="assets/target.png"><img loading="lazy" src="assets/target.png" alt="Hedef kişi"></a><figcaption>Aynı hedef kişi</figcaption></figure>')
        if case_record["status"] == "completed":
            body.append(image(run_dir / case_record["output"], identifier + "-output.png", "Ham FASHN çıktısı"))
        body.append('</div><p>' + escape(review.get("notes", "Değerlendirme bekliyor")) + '</p><table><tr>')
        body.extend('<th>' + label + '</th>' for _, label in metrics)
        body.append('</tr><tr>')
        body.extend('<td>' + escape(review.get(key, "")) + '/4</td>' for key, _ in metrics)
        body.append('</tr></table>')
        body.append(f'<p>Süre: {escape(case_record.get("elapsed_seconds", ""))} sn · <a href="{escape(case["product_url"])}">Trendyol ürün kaynağı</a></p></article>')
    body.append('<h2>Farklı üst–alt çiftleri · koruma maskeli deney</h2><p>Her çift aynı başlangıç mankeninden başlar. Önce üst, sonra alt üretilir. Korunan bölgeler ilk üst aktarımından alınır; ham ve birleştirilmiş görüntüler ayrı gösterilir. Koruma kontrolü kıyafetin doğru aktarıldığını tek başına kanıtlamaz.</p>')
    suite_path = ROOT / "runs/latest-outfit-suite.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8")) if suite_path.exists() else []
    for item in suite:
        path = ROOT / item["run_dir"]
        outfit_record = json.loads((path / "run.json").read_text(encoding="utf-8"))
        body.append('<article><h3>' + escape(item["name"]) + '</h3><div class="pictures">')
        for filename, caption in [("01-top.png", "İlk üst aktarımı"), ("02-bottom-raw.png", "Alt eklendikten sonra ham sonuç"), ("03-protected-outfit.png", "Üst korunmuş sonuç")]:
            body.append(image(path / filename, item["name"] + "-" + filename, caption))
        body.append('</div><p>' + escape(outfit_record.get("visual_review", {}).get("notes", "Görsel inceleme bekliyor")) + '</p>')
        asset(path / "run.json", item["name"] + "-run.json")
        asset(path / "selection.json", item["name"] + "-selection.json")
        body.append('<details><summary>Piksel koruma ölçümleri</summary><pre>' + escape(json.dumps(outfit_record.get("preservation_checks"), ensure_ascii=False, indent=2)) + '</pre></details></article>')
    if probe_dir:
        probe_dir = Path(probe_dir).resolve()
        body.append('<article><h2>Ayrı trençkot kategori deneyi</h2><p>Aynı ürün ve hedef, tops yerine one-pieces kategorisiyle işlendi. Bu kategori kaynak/hedef hazırlığını da değiştirir. Bu tek örnekte uzunluk ve kuşak iyileşti; ana 10 ürünlük oran değiştirilmedi.</p><div class="pictures">')
        body.append(image(run_dir / "trench-coat.png", "trench-original-category.png", "İlk tops sonucu"))
        body.append(image(probe_dir / "trench-full-coverage-probe.png", "trench-full-coverage.png", "Tam vücut kategori deneyi"))
        body.append('</div></article>')
        asset(probe_dir / "run.json", "coverage-probe-run.json")
    if suite:
        from PIL import Image, ImageOps
        preview = Image.new("RGB", (320 * len(suite), 480), "white")
        for index, item in enumerate(suite):
            source = ROOT / item["run_dir"] / "03-protected-outfit.png"
            with Image.open(source) as picture:
                thumbnail = ImageOps.contain(picture.convert("RGB"), (316, 474))
            preview.paste(thumbnail, (320*index+(320-thumbnail.width)//2, (480-thumbnail.height)//2))
        preview.save(destination / "outfit-previews.jpg", quality=94)
    body.append('<p>Başarısız sonuçlar silinmedi. Kategori/ayar denemeleri ana 10 ürünlük puana eklenmez. Tam bulgular proje docs klasöründe tutulur.</p></html>')
    report = destination / "index.html"
    report.write_text("\n".join(body), encoding="utf-8")
    # Every embedded image and local link must exist in the exported bundle.
    from html.parser import HTMLParser
    class Checker(HTMLParser):
        def handle_starttag(self, tag, attributes):
            attrs = dict(attributes)
            for key in ("src", "href"):
                value = attrs.get(key, "")
                if value.startswith("assets/") and not (destination / value).is_file():
                    raise FileNotFoundError(value)
    Checker().feed(report.read_text(encoding="utf-8"))
    archive_path = ROOT / "dist/validation-10-results.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in destination.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(destination))
    print(report)
    print(archive_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--probe", type=Path)
    args = parser.parse_args()
    build(args.run_dir, args.probe)
