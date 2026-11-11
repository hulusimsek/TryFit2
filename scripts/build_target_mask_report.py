"""Complete ten-case before/after report, including regressions and all scores."""
import argparse
import html
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[1]


def build(run_dir):
    run_dir=Path(run_dir).resolve();record=json.loads((run_dir/'run.json').read_text(encoding='utf-8'))
    quality=json.loads((run_dir/'quality.json').read_text(encoding='utf-8'))
    provenance=json.loads((run_dir/'target-mask-provenance.json').read_text(encoding='utf-8'))
    baseline=ROOT/provenance['baseline'];old=json.loads((baseline/'quality.json').read_text(encoding='utf-8'))
    manifest=json.loads((run_dir/'manifest.json').read_text(encoding='utf-8'));cases={c['id']:c for c in manifest['cases']}
    if len(record['cases'])!=10 or {c['id'] for c in record['cases']}!=set(cases) or any(c['status']!='completed' for c in record['cases']):raise ValueError('All ten actual outputs required')
    dest=ROOT/'dist/target-mask-benchmark';assets=dest/'assets';assets.mkdir(parents=True,exist_ok=True)
    esc=lambda x:html.escape(str(x),quote=True)
    def copy(path,name):shutil.copy2(path,assets/name);return 'assets/'+name
    def panel(path,name,caption):
        uri=copy(path,name);return f'<figure><a href="{esc(uri)}"><img src="{esc(uri)}" alt="{esc(caption)}" loading="lazy"></a><figcaption>{esc(caption)}</figcaption></figure>'
    body=['<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TryFit — On üründe hedef maskeleme</title>',
        '<style>body{font:16px/1.5 system-ui;max-width:1200px;margin:auto;padding:25px;background:#f5f5f0;color:#253125}article{background:white;margin:24px 0;padding:20px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}figure{margin:0}img{width:100%;height:430px;object-fit:contain}figcaption{font-size:14px}pre{white-space:pre-wrap}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>',
        '<h1>TryFit Next · Hedef maskeleme: tam on ürün kontrolü</h1>',
        f'<p><b>Önceki SAM kaynak maskeli koşu: {old["passed"]}/10. Bütün hedeflerde maskeleme açılan yeni koşu: {quality["passed"]}/10.</b> Araştırma kapısı: {esc(quality["quality_gate"])}. Puanlar asistanın görsel ön incelemesidir, bağımsız panel değildir.</p>',
        '<p>Tek değişken hedef maskelemesidir. Aynı kaynak/hedef fotoğrafları, kategoriler, SAM kaynak maskeleri, pozlar, seed 42 / 30 adım / guidance 1.5 kullanıldı. Çıktılara piksel yapıştırılmadı. Her örnek aynı başlangıç hedefinden bağımsız üretildi.</p>',
        '<p>Hedef maskeleme bütün kategorilere uygulanınca trençkot ve bel ayrıntılarında gerileme görüldü. Bu yöntem tüm ürünlere varsayılan yapılmadı. Yerel deneme ekranı, daha önce farklı profillerde sınanan ayrı iki-aşamalı protokolü kullanır: üstte hedef maskesiz, altta hedef maskeli. On ürünlük bu koşu o karma iki-parça protokolünün kalite oranı değildir.</p>',
        '<p>Ürün boyu, gerçek beden uyumu ve boy/kilodan vücut hesaplama doğrulanmadı. Kaynak maskeleri araştırmacı desteklidir; insan ayrıştırıcısının araştırma lisansı kısıtı sürer. Eski koşular ve puanlar değiştirilmedi.</p>',
        '<p><a href="assets/review.csv">Yeni puanlar</a> · <a href="assets/baseline-review.csv">Önceki puanlar</a> · <a href="assets/run.json">Çalıştırma kaydı</a> · <a href="assets/target-mask-provenance.json">Kontrol edilen değişkenler</a></p>']
    for name in ['run.json','review.csv','quality.json','manifest.json','target-mask-provenance.json','pip-freeze.txt']:copy(run_dir/name,name)
    copy(baseline/'review.csv','baseline-review.csv')
    for item in record['cases']:
        ident=item['id'];case=cases[ident];decision=next(d for d in quality['decisions'] if d['id']==ident);previous=next(d for d in old['decisions'] if d['id']==ident)
        body.append('<article><h2>'+esc(case['label'])+' · '+esc(previous['decision'])+' → '+esc(decision['decision'])+'</h2><div class="grid">')
        paths=[ROOT/case['image'],baseline/(ident+'.png'),run_dir/(ident+'.png')]
        for i,(path,caption) in enumerate(zip(paths,['Aynı ürün kaynağı','Önceki: SAM kaynak maskesi, hedef maskesiz','Yeni: aynı kaynak maskesi, hedef maskeli'])):body.append(panel(path,ident+'-'+str(i)+path.suffix,caption))
        body.append('</div><p>'+esc(decision['review']['notes'])+'</p></article>')
        board=Image.new('RGB',(900,500),'#f5f5f0');draw=ImageDraw.Draw(board)
        for i,path in enumerate(paths):
            picture=ImageOps.contain(Image.open(path).convert('RGB'),(290,460));board.paste(picture,(i*300+(300-picture.width)//2,30+(460-picture.height)//2));draw.text((i*300+7,8),['SOURCE','TARGET MASKLESS','TARGET MASKED'][i],fill='black')
        board.save(dest/(ident+'-comparison.jpg'),quality=92)
    body.append('</html>');(dest/'index.html').write_text('\n'.join(body),encoding='utf-8')
    with zipfile.ZipFile(ROOT/'dist/target-mask-benchmark-results.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dest.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(dest.parent))
    print(dest/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_dir',type=Path);build(parser.parse_args().run_dir)
