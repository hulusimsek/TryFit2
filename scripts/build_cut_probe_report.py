"""Bundle every bounded cut/pose probe; never select only favorable outputs."""
import argparse
import html
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
IDS = ['oversize-hoodie', 'denim-jacket', 'hooded-sweatshirt']


def build(pose_dir, cutout_dir, sampling_dir):
    pose_dir, cutout_dir = Path(pose_dir).resolve(), Path(cutout_dir).resolve()
    sampling_dir = Path(sampling_dir).resolve()
    baseline = ROOT/'runs/20261110T095148Z-cf9135a6'
    manifest = json.loads((baseline/'manifest.json').read_text(encoding='utf-8'))
    cases = {c['id']: c for c in manifest['cases']}
    for directory in [pose_dir, cutout_dir, sampling_dir]:
        record = json.loads((directory/'run.json').read_text(encoding='utf-8'))
        if {c['id'] for c in record['cases']} != set(IDS) or any(c['status'] != 'completed' for c in record['cases']):
            raise ValueError('All three probes must complete')
    dest = ROOT/'dist/cut-probes'
    assets = dest/'assets'
    assets.mkdir(parents=True,exist_ok=True)
    esc = lambda value: html.escape(str(value), quote=True)
    body = ['<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TryFit — Kesim denemeleri</title>',
        '<style>body{font:16px/1.5 system-ui;max-width:1400px;margin:auto;padding:24px;background:#f5f5f0}article{background:white;padding:20px;margin:24px 0}.grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}figure{margin:0}img{width:100%;height:400px;object-fit:contain}figcaption{font-size:14px}@media(max-width:700px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>',
        '<h1>TryFit Next · Üç zor üründe kesim denemeleri</h1>',
        '<p>Aynı hedef, kategori ve seed 42. İlk varyant kaynak pozu yerine boş poz verir; SAM maskesi korunur. İkinci varyant SAM cutout görselini flat-lay dalıyla işler: kaynak pozu boş olur, maske pre-resize öncesinde uygulanır. Pinned modelde ayrı fotoğraf-türü embedding girdisi yoktur; ilk iki varyant büyük ölçüde örtüşür ve bağımsız iki çözüm sayılmaz. Cutout gerçek düz serilmiş fotoğraf değildir. Son varyant kaynak pozunu koruyup adımı 30→50 ve guidance değerini 1.5→2.5 değiştirir; iki ayarın etkisi tek tek ayrıştırılmadı.</p>',
        '<p>Bu küçük deneyler önceki 7/10 sonucunu değiştirmez. Üç üründen oluşan koşular genel kalite kapısını geçiremez. Bütün dokuz yeni çıktı aşağıda gösterilir. Puanlar asistanın görsel ön incelemesidir; gerçek beden doğruluğu ölçülmedi.</p>']
    for prefix,directory in [('pose',pose_dir),('cutout',cutout_dir),('sampling',sampling_dir)]:
        for name in ['run.json','quality.json','review.csv','manifest.json']:
            shutil.copy2(directory/name,assets/(prefix+'-'+name))
        for name in ['source-mask-provenance.json','probe.json']:
            if (directory/name).exists():shutil.copy2(directory/name,assets/(prefix+'-'+name))
        body.append(f'<p>{prefix}: <a href="assets/{prefix}-review.csv">Puanlar</a> · <a href="assets/{prefix}-run.json">Çalıştırma kaydı</a></p>')
    for identifier in IDS:
        case=cases[identifier]
        body.append('<article><h2>'+esc(case['label'])+'</h2><div class="grid">')
        paths=[ROOT/case['image'],baseline/(identifier+'.png'),pose_dir/(identifier+'.png'),cutout_dir/(identifier+'.png'),sampling_dir/(identifier+'.png')]
        captions=['Kaynak ürün','Önceki SAM maskeli sonuç','Kaynak pozu kaldırılmış','Kıyafet cutout + flat-lay dalı','50 adım / guidance 2.5 / kaynak pozlu']
        board=Image.new('RGB',(1250,470),'#f5f5f0');draw=ImageDraw.Draw(board)
        for i,(path,caption) in enumerate(zip(paths,captions)):
            name=identifier+'-'+str(i)+path.suffix
            shutil.copy2(path,assets/name)
            body.append(f'<figure><a href="assets/{esc(name)}"><img src="assets/{esc(name)}" alt="{esc(caption)}"></a><figcaption>{esc(caption)}</figcaption></figure>')
            image=ImageOps.contain(Image.open(path).convert('RGB'),(244,430))
            board.paste(image,(i*250+(250-image.width)//2,30+(430-image.height)//2))
            draw.text((i*250+5,8),['SOURCE','BASELINE','NO SOURCE POSE','CUTOUT / FLAT-LAY','50 STEPS / GUIDANCE 2.5'][i],fill='black')
        board.save(dest/(identifier+'-probes.jpg'),quality=92)
        body.append('</div>')
        for label,directory in [('Boş kaynak pozu',pose_dir),('Cutout/flat-lay',cutout_dir),('50 adım / guidance 2.5',sampling_dir)]:
            quality=json.loads((directory/'quality.json').read_text(encoding='utf-8'))
            decision=next(c for c in quality['decisions'] if c['id']==identifier)
            body.append('<p><b>'+esc(label)+': '+esc(decision['decision'])+'</b> · '+esc(decision['review'].get('notes',''))+'</p>')
        body.append('</article>')
    body.append('</html>')
    (dest/'index.html').write_text('\n'.join(body),encoding='utf-8')
    with zipfile.ZipFile(ROOT/'dist/cut-probes-results.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(dest.rglob('*')):
            if p.is_file():archive.write(p,p.relative_to(dest.parent))
    print(dest/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pose',type=Path);parser.add_argument('cutout',type=Path);parser.add_argument('sampling',type=Path)
    args=parser.parse_args();build(args.pose,args.cutout,args.sampling)
