"""Portable report showing raw neural inference and explicitly labeled repaint."""
import argparse
import html
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT=Path(__file__).resolve().parents[1]


def build(run_dir,flatlay_dirs=None):
    run_dir=Path(run_dir).resolve()
    record=json.loads((run_dir/'run.json').read_text(encoding='utf-8'))
    quality=json.loads((run_dir/'quality.json').read_text(encoding='utf-8'))
    manifest=json.loads((run_dir/'manifest.json').read_text(encoding='utf-8'))
    cases={c['id']:c for c in manifest['cases']}
    if len(record['cases'])!=3 or any(c['status']!='completed' for c in record['cases']):
        raise ValueError('Report requires all three actual CatVTON outputs')
    dest=ROOT/'dist/catvton-comparison';assets=dest/'assets';assets.mkdir(parents=True,exist_ok=True)
    esc=lambda x:html.escape(str(x),quote=True)
    def copy(path,name):
        shutil.copy2(path,assets/name)
        return 'assets/'+name
    def panel(path,name,caption):
        url=copy(path,name)
        return f'<figure><a href="{esc(url)}"><img src="{esc(url)}" alt="{esc(caption)}" loading="lazy"></a><figcaption>{esc(caption)}</figcaption></figure>'
    body=['<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TryFit — CatVTON karşılaştırması</title>',
        '<style>body{font:16px/1.5 system-ui;max-width:1450px;margin:auto;padding:24px;background:#f5f5f0;color:#232723}article{background:white;padding:20px;margin:24px 0}.grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}figure{margin:0}img{width:100%;height:400px;object-fit:contain;background:#eee}figcaption{font-size:14px}.inputs{display:flex;gap:20px}.inputs figure{max-width:300px}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:800px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>',
        '<h1>TryFit Next · FASHN ve CatVTON karşılaştırması</h1>',
        f'<p><b>CatVTON görsel ön değerlendirme: {quality["passed"]}/3.</b> Üç zor örnekten oluşur; genel on ürünlük kalite kapısı geçilmedi. Önceki 7/10 koşusu değiştirilmedi. Puanlar asistanın görsel ön incelemesidir; bağımsız insan paneli değildir.</p>',
        '<p>Aynı sentetik manken ve aynı üç Trendyol ürünü. CatVTON mix-48k-1024: 50 adım, guidance 2.5, seed 42, 768×1024 tuval. Kıyafet girdisi aynı SAM maskesindeki görünür kumaşın beyaz zeminli kesitidir. Hedefe araştırmacı tarafından aynı üst-gövde maskesi uygulandı. FASHN farklı çözünürlük ve maskeleme yöntemi kullanır; bu karşılaştırma yalnızca model mimarisinin etkisini ayırmaz.</p>',
        '<p>CatVTON ham sonucu ve resmî isteğe bağlı repaint işlemi ayrı gösterilir. Değerlendirilen ana çıktı repaint uygulanmış görüntüdür: maske dışında orijinal manken pikselleri geri konur, maske içinde gerçek CatVTON üretimi kalır. Bu yüzden dış bölgelerin korunması tek başına modelin kimlik/vücut koruma yeteneği değildir. Üst-gövde maskesi ve kaynak kıyafet seçimi otomatik değildir.</p>',
        '<p>175 cm / 65 kg görsel profildir; ölçülü vücut, ürün bedeni veya gerçek kumaş fiziği doğrulanmadı. CatVTON kod/ağırlıkları CC BY-NC-SA 4.0 altında yalnızca ticari olmayan kullanım içindir; burada araştırma karşılaştırmasıdır.</p>',
        '<p><a href="assets/review.csv">Puanlar</a> · <a href="assets/run.json">Çalıştırma ve ağırlık kaynakları</a> · <a href="assets/pip-freeze.txt">Ortam</a></p><h2>Sabit hedef ve maske</h2><div class="inputs">']
    for name in ['run.json','quality.json','review.csv','pip-freeze.txt','manifest.json']:
        copy(run_dir/name,name)
    for name,caption in [('target-canvas.png','Kırpılmadan hazırlanmış aynı hedef'),('target-mask-overlay.jpg','Araştırmacının üst-gövde zarfı'),('target-mask-blurred.png','Üretim ve repaint maskesi')]:
        body.append(panel(run_dir/name,name,caption))
    body.append('</div>')
    baseline=ROOT/record['baseline']
    for item in record['cases']:
        identifier=item['id'];case=cases[identifier]
        decision=next(c for c in quality['decisions'] if c['id']==identifier)
        body.append('<article><h2>'+esc(case['label'])+' · '+esc(decision['decision'])+'</h2><div class="grid">')
        paths=[ROOT/case['image'],run_dir/(identifier+'-condition.png'),baseline/(identifier+'.png'),run_dir/item['raw_output'],run_dir/item['output']]
        captions=['Orijinal kaynak','CatVTON kıyafet girdisi','Önceki FASHN + SAM sonucu','CatVTON ham sinir ağı çıktısı','CatVTON + açıkça belirtilen repaint']
        board=Image.new('RGB',(1250,470),'#f5f5f0');draw=ImageDraw.Draw(board)
        for i,(path,caption) in enumerate(zip(paths,captions)):
            body.append(panel(path,identifier+'-'+str(i)+path.suffix,caption))
            picture=ImageOps.contain(Image.open(path).convert('RGB'),(244,430))
            board.paste(picture,(i*250+(250-picture.width)//2,30+(430-picture.height)//2))
            draw.text((i*250+5,8),['SOURCE','GARMENT INPUT','FASHN + SAM','CATVTON RAW','CATVTON + REPAINT'][i],fill='black')
        board.save(dest/(identifier+'-models.jpg'),quality=92)
        body.append('</div><p>'+esc(decision['review'].get('notes',''))+'</p>')
        body.append('<p>Gerçek süre: '+esc(item['elapsed_seconds'])+' sn; PyTorch tepe allocated: '+esc(item['peak_allocated_gib'])+' GiB. Sürücü/masaüstü belleği buna dahil değildir.</p></article>')
    for control_index,flatlay_dir in enumerate(flatlay_dirs or []):
        flatlay_dir=Path(flatlay_dir).resolve()
        control=json.loads((flatlay_dir/'run.json').read_text(encoding='utf-8'))
        control_quality=json.loads((flatlay_dir/'quality.json').read_text(encoding='utf-8'))
        control_manifest=json.loads((flatlay_dir/'manifest.json').read_text(encoding='utf-8'))
        if len(control['cases'])!=1 or control['cases'][0]['status']!='completed' or control['experiment_scope']!='separate real flat-lay hoodie control':
            raise ValueError('Invalid separate flat-lay control')
        control_case=next(c for c in control_manifest['cases'] if c['id']=='oversize-hoodie')
        prefix='flatlay-'+str(control_index)+'-'
        body.append('<article><h2>Ayrı kaynak kontrolü '+str(control_index+1)+': gerçek düz ürün fotoğrafı</h2><p>Bu görsel aynı hoodie ürününün galerisindendir. Kaynak değiştiği için üstteki üç mankenli kaynak testinin payına eklenmez. Ön sonuç: '+esc(control_quality['decisions'][0]['decision'])+'. Her kontrolün hedef maskesi de aşağıda gösterilir.</p><div class="grid">')
        for source,name,caption in [(ROOT/control_case['image'],'flatlay-source.jpg','Aynı ürünün gerçek düz fotoğrafı'),(flatlay_dir/'oversize-hoodie-raw.png','flatlay-raw.png','Bu kaynakla ham CatVTON çıktısı'),(flatlay_dir/'oversize-hoodie.png','flatlay-repaint.png','Bu kaynakla CatVTON + repaint')]:
            body.append(panel(source,prefix+name,caption))
        body.append(panel(flatlay_dir/'target-mask-overlay.jpg',prefix+'mask-overlay.jpg','Bu kontrolün hedef maskesi'))
        body.append('</div><p>'+esc(control_quality['decisions'][0]['review'].get('notes',''))+'</p></article>')
        for name in ['run.json','review.csv','quality.json','manifest.json']:
            copy(flatlay_dir/name,prefix+name)
    body.append('</html>')
    (dest/'index.html').write_text('\n'.join(body),encoding='utf-8')
    with zipfile.ZipFile(ROOT/'dist/catvton-comparison-results.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dest.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(dest.parent))
    print(dest/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_dir',type=Path);parser.add_argument('--flatlay',type=Path,action='append')
    args=parser.parse_args();build(args.run_dir,args.flatlay)
