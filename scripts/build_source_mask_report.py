"""Bundle the controlled garment-isolation experiment with frozen baseline images."""
import argparse
import html
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def build(run_dir):
    run_dir = Path(run_dir).resolve()
    record = json.loads((run_dir / 'run.json').read_text(encoding='utf-8'))
    quality = json.loads((run_dir / 'quality.json').read_text(encoding='utf-8'))
    provenance = json.loads((run_dir / 'source-mask-provenance.json').read_text(encoding='utf-8'))
    baseline = ROOT / provenance['baseline']
    manifest = json.loads((run_dir / 'manifest.json').read_text(encoding='utf-8'))
    cases = {c['id']: c for c in manifest['cases']}
    if (len(cases) != 10 or {c['id'] for c in record['cases']} != set(cases)
            or any(c['status'] != 'completed' for c in record['cases'])):
        raise ValueError('Before/after report requires all ten completed cases')
    decisions = {d['id']: d for d in quality['decisions']}
    destination = ROOT / 'dist/source-isolation'
    assets = destination / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    esc = lambda v: html.escape(str(v), quote=True)

    def copy(source, name):
        shutil.copy2(source, assets / name)
        return 'assets/' + name

    def panel(source, name, caption):
        uri = copy(source, name)
        return f'<figure><a href="{esc(uri)}"><img src="{esc(uri)}" alt="{esc(caption)}" loading="lazy"></a><figcaption>{esc(caption)}</figcaption></figure>'

    parts = ['<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TryFit — Kıyafet ayırma deneyi</title>',
        '<style>body{font:16px/1.5 system-ui;max-width:1300px;margin:auto;padding:24px;background:#f4f4f0;color:#202320}article{background:white;padding:20px;margin:24px 0;border-radius:12px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}figure{margin:0}img{width:100%;height:400px;object-fit:contain;background:#eee}figcaption{font-size:14px}a{color:#27533f}pre{white-space:pre-wrap}@media(max-width:760px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}img{height:300px}}</style>',
        '<h1>TryFit Next · Seçilen kıyafeti ayırma deneyi</h1>',
        f'<p><b>Yeni görsel ön değerlendirme: {quality["passed"]}/10. Kalite kapısı: {esc(quality["quality_gate"])}.</b> Önceki tur 4/10. Bağımsız insan paneli değildir.</p>',
        '<p>Aynı on ürün, aynı sentetik hedef, aynı kategori ve aynı seed 42 / 30 adım / guidance 1.5. Değişiklik: kaynak kıyafet maskesi. Kaynağın duruş bilgisi orijinal fotoğraftan alındı. SAM2.1 için ürün ve hariç tutulacak parçalar araştırmacı tarafından noktalarla işaretlendi; otomatik ürün seçimi gösterilmedi.</p>',
        '<p>Maskeler görünür kumaşı ayırır; saç, el veya çanta arkasında kalan kumaş yeniden oluşturulmaz. 175 cm / 65 kg hedef profili gerçek beden uyumu veya ölçülü vücut modellemesi kanıtı değildir. FASHN insan ayrıştırıcısının araştırma lisansı kısıtı devam eder.</p>',
        '<p><a href="assets/review.csv">Puanlar</a> · <a href="assets/run.json">Deney kaydı</a> · <a href="assets/source-mask-provenance.json">Maskeler ve işaretlemeler</a></p>']
    for name in ['run.json', 'review.csv', 'quality.json', 'source-mask-provenance.json', 'manifest.json', 'pip-freeze.txt']:
        copy(run_dir / name, name)
    for item in record['cases']:
        identifier = item['id']
        case = cases[identifier]
        extraction = ROOT / provenance['extractions'][identifier]['directory']
        decision = decisions[identifier]
        parts.append(f'<article><h2>{esc(case["label"])} · {esc(decision["decision"])}</h2><div class="grid">')
        paths = [ROOT / case['image'], baseline / f'{identifier}.png', extraction / 'isolated.png', run_dir / f'{identifier}.png']
        captions = ['Ürün kaynağı', 'Önceki sonuç', 'SAM2 ile seçilen kıyafet', 'Yeni gerçek VTON çıktısı']
        for index, (path, caption) in enumerate(zip(paths, captions)):
            parts.append(panel(path, f'{identifier}-{index}{path.suffix}', caption))
        copy(extraction / 'mask.png', f'{identifier}-mask.png')
        parts.append('</div><p>' + esc(decision.get('review', {}).get('notes', '')) + '</p></article>')
        # A compact source/before/after board for inline inspection.
        board = Image.new('RGB', (900, 500), '#f3f3ef')
        draw = ImageDraw.Draw(board)
        for index, (path, caption) in enumerate(zip([paths[0], paths[1], paths[3]], ['SOURCE', 'BEFORE', 'AFTER SOURCE ISOLATION'])):
            picture = ImageOps.contain(Image.open(path).convert('RGB'), (292, 465))
            board.paste(picture, (index*300+(300-picture.width)//2, 28+(465-picture.height)//2))
            draw.text((index*300+8, 8), caption, fill='#202320')
        board.save(destination / f'{identifier}-before-after.jpg', quality=92)
    parts.append('</html>')
    (destination / 'index.html').write_text('\n'.join(parts), encoding='utf-8')
    archive = ROOT / 'dist/source-isolation-results.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(destination.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(destination.parent))
    print(destination / 'index.html')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=Path)
    build(parser.parse_args().run_dir)
