"""Display distinct synthetic targets and actual VTON results without fit claims."""
import argparse
import html
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[1]


def build(suite_dir):
    suite_dir=Path(suite_dir).resolve()
    record=json.loads((suite_dir/'suite.json').read_text(encoding='utf-8'))
    if record['status']!='completed' or len(record['profiles'])!=3 or any(p['status']!='completed' for p in record['profiles']):
        raise ValueError('All three real two-stage outfit runs required')
    dest=ROOT/'dist/avatar-suite';assets=dest/'assets';assets.mkdir(parents=True,exist_ok=True)
    esc=lambda value:html.escape(str(value),quote=True)
    def copy(path,name):
        shutil.copy2(path,assets/name);return 'assets/'+name
    def panel(path,name,caption):
        uri=copy(path,name)
        return f'<figure><a href="{esc(uri)}"><img src="{esc(uri)}" alt="{esc(caption)}"></a><figcaption>{esc(caption)}</figcaption></figure>'
    body=['<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TryFit — Üç görsel manken profili</title>',
        '<style>body{font:16px/1.5 system-ui;max-width:1450px;margin:auto;padding:24px;background:#f5f5f0;color:#222822}article{background:white;padding:20px;margin:24px 0}.grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px}figure{margin:0}img{width:100%;height:420px;object-fit:contain;background:#eee}figcaption{font-size:14px}pre{white-space:pre-wrap;overflow-wrap:anywhere}.note{background:#fff3cc;padding:15px}@media(max-width:760px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>',
        '<h1>TryFit Next · Aynı kombin, üç farklı görsel manken</h1>',
        '<p class="note"><b>Bu bir ölçülü beden veya ürün bedeni simülasyonu değildir.</b> İnce, orta ve dolgun görünüm için üç farklı sentetik hedef görüntüsü kullanıldı. Boy/kilo değerleri yalnızca örnek profil etiketleridir; sayıdan hesaplanmış vücut şekli, gerçek kıyafet bedeni veya oturuş garantisi yoktur. Görsellerin kamera ölçekleri de fiziksel boy karşılaştırması için kalibre edilmedi.</p>',
        '<p>Başlangıçtaki gri tişört/legging mankenleri built-in image_gen ile hazırlanmış görsel girdilerdir. Siyah tişört ve siyah pantolonlar bu araçla çizdirilmedi: her profilde iki yeni yerel FASHN VTON inference çalıştı. Aynı ürün fotoğrafları, aynı araştırmacı destekli SAM kaynak maskeleri, seed 42 / 30 adım / guidance 1.5 kullanıldı. Üçü de kendi başlangıç görüntüsünden başlatıldı.</p>',
        '<p>Ham ikinci üretim ana önizlemedir. Üst-koruma sürümü ayrı gösterilir; ilk üst çıktısından yüz/saç/tişört/kol/el bölgelerini geri yerleştirir ve sınır izi bırakabilir. Kaynak pantolonun ürün görselinde AI üretimi etiketi vardır. Genel on ürünlük 7/10 ön sonuç değişmedi; bu üç sentetik örnek genel kullanıcı başarısını kanıtlamaz.</p>',
        '<p><b>Dolgun profilde ayak bölgesi hatası var.</b> Ayak piksellerini hedef görselden geri alma denemesi de yapıldı; pantolon/ayak sınırında kesik izleri bıraktığı için ana sonuç seçilmedi. Bu kompozitler açıkça etiketlenerek ayrıca gösterilir; modelin doğal koruması veya tamamlanmış düzeltme olarak sunulmaz.</p>',
        '<p><a href="assets/suite.json">Koşu ve profil kayıtları</a> · <a href="assets/generation-prompts.json">Yeni mankenler için kullanılan tam promptlar</a> · <a href="assets/baseline-prompt.md">Orta mankenin önceki promptu</a></p>']
    copy(suite_dir/'suite.json','suite.json')
    copy(ROOT/'evaluation/annotations/avatar-profile-generation.json','generation-prompts.json')
    copy(ROOT/'docs/avatar-baseline.md','baseline-prompt.md')
    final_board=Image.new('RGB',(1080,600),'#f5f5f0');full_board=Image.new('RGB',(1080,1180),'#f5f5f0')
    final_draw=ImageDraw.Draw(final_board);full_draw=ImageDraw.Draw(full_board)
    labels={'slender':'INCE GORUNUM','medium':'ORTA GORUNUM','fuller':'DOLGUN GORUNUM'}
    for i,item in enumerate(record['profiles']):
        profile=next(p for p in record['catalog']['profiles'] if p['id']==item['id'])
        directory=ROOT/item['run_dir']
        body.append('<article><h2>'+esc(item['label'])+'</h2><p>Örnek etiket: '+esc(profile['height_cm'])+' cm / '+esc(profile['weight_kg'])+' kg — ölçülmüş değildir.</p><div class="grid">')
        entries=[(ROOT/item['avatar_image'],'input.png','Sentetik başlangıç hedefi'),(directory/'01-top.png','top.png','Gerçek VTON: önce seçilen tişört'),(directory/'02-bottom-raw.png','outfit.png','Gerçek VTON: pantolon eklendikten sonra ham kombin'),(directory/'03-protected-outfit.png','protected.png','Aynı sonuç + açıkça belirtilen üst koruma')]
        if item.get('foot_preservation'):
            entries.append((directory/'04-feet-preserved.png','feet-experiment.png','Ayrı ayak kompoziti denemesi — sınır izi nedeniyle seçilmedi'))
        for source,name,caption in entries:
            body.append(panel(source,item['id']+'-'+name,caption))
        body.append('</div>')
        review=item.get('review',{})
        if review:body.append('<p>'+esc(review.get('notes',''))+'</p><p>Ön karar: '+esc(review.get('decision','not_reviewed'))+'</p>')
        body.append('</article>')
        for name in ['run.json','selection.json','upper-protection-mask.png']:
            copy(directory/name,item['id']+'-'+name)
        if item.get('foot_preservation'):
            copy(directory/'foot-preservation.json',item['id']+'-foot-preservation.json')
            copy(directory/'foot-preservation-mask.png',item['id']+'-foot-mask.png')
        for board,draw,pictures in [(final_board,final_draw,[(directory/'02-bottom-raw.png',0)]),(full_board,full_draw,[(ROOT/item['avatar_image'],0),(directory/'02-bottom-raw.png',580)])]:
            for source,y in pictures:
                picture=ImageOps.contain(Image.open(source).convert('RGB'),(350,550));board.paste(picture,(i*360+(360-picture.width)//2,y+35+(550-picture.height)//2))
                draw.text((i*360+12,y+10),labels[item['id']]+(' / INPUT' if source==ROOT/item['avatar_image'] else ' / VTON'),fill='black')
                if item['id']=='fuller' and source!=ROOT/item['avatar_image']:
                    draw.text((i*360+12,y+23),'AYAK BOLGESI DUZELTME GEREKIYOR',fill='#9c3027')
    body.append('</html>')
    final_board.save(dest/'three-outfits.jpg',quality=94);full_board.save(dest/'before-after.jpg',quality=94)
    (dest/'index.html').write_text('\n'.join(body),encoding='utf-8')
    with zipfile.ZipFile(ROOT/'dist/avatar-suite-results.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dest.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(dest.parent))
    print(dest/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('suite_dir',type=Path);build(parser.parse_args().suite_dir)
