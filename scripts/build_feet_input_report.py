"""Compare every frozen maskless baseline with actual target-masked inference."""
import argparse
import html
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[1]


def build(run_dir):
    run_dir=Path(run_dir).resolve()
    record=json.loads((run_dir/'run.json').read_text(encoding='utf-8'))
    if record['status']!='completed' or len(record['profiles'])!=3 or any(p['status']!='completed' for p in record['profiles']):
        raise ValueError('Three complete real inference results required')
    dest=ROOT/'dist/feet-input';assets=dest/'assets';assets.mkdir(parents=True,exist_ok=True)
    esc=lambda x:html.escape(str(x),quote=True)
    def copy(path,name):shutil.copy2(path,assets/name);return 'assets/'+name
    def panel(path,name,caption):
        uri=copy(path,name)
        return f'<figure><a href="{esc(uri)}"><img src="{esc(uri)}" alt="{esc(caption)}"></a><figcaption>{esc(caption)}</figcaption></figure>'
    body=['<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TryFit — Ayak bilgisiyle pantolon üretimi</title>',
        '<style>body{font:16px/1.5 system-ui;max-width:1400px;margin:auto;padding:24px;background:#f5f5f0;color:#232823}article{background:white;margin:24px 0;padding:20px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}figure{margin:0}img{width:100%;height:430px;object-fit:contain}figcaption{font-size:14px}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:760px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>',
        '<h1>TryFit Next · Ayakları girdide koruyarak pantolon üretme</h1>',
        '<p>Tek değişiklik: pantolon aşamasında hedef kıyafetin maskelenmesi (segmentation_free=False). Aynı önceki tişört çıktısı, aynı pantolon/SAM kaynak maskesi, seed 42, 30 adım ve guidance 1.5 kullanıldı. İlk tişört aşaması yeniden çalıştırılmadı.</p>',
        '<p><b>Yeni görüntüler gerçek FASHN çıktısıdır; üretimden sonra ayak veya üst pikseli geri yapıştırılmadı.</b> Önceki piksel-kopyalama denemesinin kesik sınırları bu yöntemle karıştırılmaz. Maskeli hedef hazırlığı ayakları büyük ölçüde girdi görüntüsünde bırakır; sınırda değişen ayak pikselleri kayıtlıdır. Bu, ağın pikselleri birebir koruduğu anlamına gelmez.</p>',
        '<p>Üç hazır sentetik görünüm kullanılır. Boy/kilodan ölçülü vücut hesaplama, gerçek ürün bedeni veya paça boyu doğrulaması yoktur. Maskeleme paça boyunu, bel ayrıntılarını ve vücut görünümünü değiştirebilir. Genel on ürünlük 7/10 ön sonuç bu küçük testle değişmez.</p>',
        '<p><a href="assets/run.json">Tam ayarlar, kaynaklar ve ön inceleme</a></p>']
    copy(run_dir/'run.json','run.json')
    board=Image.new('RGB',(1080,600),'#f5f5f0');draw=ImageDraw.Draw(board)
    before_after=Image.new('RGB',(1080,1180),'#f5f5f0');full_draw=ImageDraw.Draw(before_after)
    labels={'slender':'INCE','medium':'ORTA','fuller':'DOLGUN'}
    for i,item in enumerate(record['profiles']):
        body.append('<article><h2>'+esc(item['label'])+'</h2><div class="grid">')
        entries=[(ROOT/item['person_image'],'top.png','Aynı ilk aşama: tişört, ayaklar görünür'),(ROOT/item['previous_raw'],'before.png','Önceki pantolon üretimi: maskesiz hedef'),(run_dir/(item['id']+'-masked-input.png'),'conditioning.png','Yeni hedef girdisi: kıyafet alanı maskeli'),(run_dir/item['output'],'after.png','Yeni ham inference — kompozit işlem yok')]
        for path,name,caption in entries:body.append(panel(path,item['id']+'-'+name,caption))
        body.append('</div><p>'+esc(item.get('review',{}).get('notes','Henüz puanlanmadı'))+'</p>')
        body.append('<p>Gerçek inference süresi: '+esc(item['elapsed_seconds'])+' sn. Hedef hazırlığında ayak etiketli '+esc(item['conditioning_feet_pixels'])+' pikselden '+esc(item['conditioning_changed_feet_pixels'])+' piksel değişti; tamamının birebir korunması iddia edilmez.</p></article>')
        for target,drawing,pictures in [(board,draw,[(run_dir/item['output'],0)]),(before_after,full_draw,[(ROOT/item['previous_raw'],0),(run_dir/item['output'],580)])]:
            for path,y in pictures:
                picture=ImageOps.contain(Image.open(path).convert('RGB'),(350,550));target.paste(picture,(i*360+(360-picture.width)//2,y+35+(550-picture.height)//2));drawing.text((i*360+12,y+10),labels[item['id']]+(' / ONCE' if path==ROOT/item['previous_raw'] else ' / YENI HAM VTON'),fill='black')
    board.save(dest/'three-outfits.jpg',quality=94);before_after.save(dest/'before-after.jpg',quality=94)
    body.append('</html>');(dest/'index.html').write_text('\n'.join(body),encoding='utf-8')
    with zipfile.ZipFile(ROOT/'dist/feet-input-results.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dest.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(dest.parent))
    print(dest/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_dir',type=Path);build(parser.parse_args().run_dir)
