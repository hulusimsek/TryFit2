"""Portable inspection report for the actual two-source outfit experiment."""
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
    if record['status']!='completed':raise ValueError('Real completed outfit required')
    selection=json.loads((run_dir/'selection.json').read_text(encoding='utf-8'))
    review=run_dir/'outfit-review.json'
    review_data=json.loads(review.read_text(encoding='utf-8')) if review.exists() else {}
    preferred=review_data.get('preferred_output','03-protected-outfit.png')
    if preferred not in {'02-bottom-raw.png','03-protected-outfit.png'}:
        raise ValueError('Invalid preferred outfit output')
    dest=ROOT/'dist/masked-outfit';assets=dest/'assets';assets.mkdir(parents=True,exist_ok=True)
    esc=lambda value:html.escape(str(value),quote=True)
    def panel(path,name,caption):
        shutil.copy2(path,assets/name)
        return f'<figure><a href="assets/{esc(name)}"><img src="assets/{esc(name)}" alt="{esc(caption)}"></a><figcaption>{esc(caption)}</figcaption></figure>'
    body=['<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TryFit — Gerçek iki parçalı kombin</title>',
        '<style>body{font:16px/1.5 system-ui;max-width:1250px;margin:auto;padding:24px;background:#f5f5f0;color:#202520}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:25px 0}figure{margin:0;background:white;padding:10px}img{width:100%;height:440px;object-fit:contain}figcaption{font-size:14px}pre{white-space:pre-wrap}@media(max-width:650px){.grid{grid-template-columns:1fr}}</style>',
        '<h1>TryFit Next · Tişört ve pantolon birlikte</h1>',
        '<p>Aynı başlangıç mankenine önce seçilmiş tişört, sonra seçilmiş pantolon gerçek FASHN VTON inference ile uygulanır. Her iki kaynakta araştırmacının SAM kıyafet maskesi kullanılır; kaynak pozu orijinal fotoğraftan hesaplanır. Ham iki parça sonucu ve üst kıyafet koruma uygulanmış sürüm ayrı gösterilir.</p>',
        f'<p>Deneme profili: {esc(selection["avatar"]["height_cm"])} cm / {esc(selection["avatar"]["weight_kg"])} kg. Bu bilgiler kullanıcıya göre değişen profil alanlarıdır; bu mankenin gerçek ölçülerinin eşleştiği doğrulanmadı. Kaynak seçimi otomatik değildir. Genel 7/10 ön değerlendirme değişmedi; tek kombin genel kalite kapısını geçiremez.</p>',
        '<p>Üst koruma, ilk çıktının tişört/yüz/saç/kol/el bölgelerini ikinci çıktıya geri yerleştirir. Bu, ikinci modelin üstü doğal olarak koruduğu anlamına gelmez. Üç piksellik yumuşatılmış sınır ve örtüşmeler ayrıca incelenmelidir. FASHN insan ayrıştırıcısının araştırma lisansı kısıtı sürer.</p><div class="grid">']
    body.append(panel(ROOT/selection['avatar']['image'],'avatar.png','Başlangıç mankeni'))
    for item in selection['items']:
        body.append(panel(ROOT/item['image'],item['id']+'-source.jpg',item['label']+' — gerçek kaynak'))
    body.append('</div><div class="grid">')
    for name,caption in [('01-top.png','İlk gerçek üretim: seçilen tişört'),('02-bottom-raw.png','İkinci gerçek üretim: pantolon eklendi, ham sonuç'),('03-protected-outfit.png','Aynı ikinci sonuç + açıkça belirtilen üst koruma')]:
        body.append(panel(run_dir/name,name,caption))
    body.append('</div>')
    if review.exists():
        body.append('<h2>Görsel ön inceleme</h2><pre>'+esc(review.read_text(encoding='utf-8'))+'</pre>')
        shutil.copy2(review,assets/review.name)
    body.append('<p><a href="assets/run.json">Çalıştırma kaydı</a> · <a href="assets/source-mask-provenance.json">Kaynak maskeleri</a></p></html>')
    for name in ['run.json','selection.json','source-mask-provenance.json','upper-protection-mask.png']:
        shutil.copy2(run_dir/name,assets/name)
    shutil.copy2(run_dir/preferred,dest/'outfit.png')
    pictures=[('SOURCE TOP',ROOT/selection['items'][0]['image']),('SOURCE BOTTOM',ROOT/selection['items'][1]['image']),('RAW OUTFIT',run_dir/'02-bottom-raw.png'),('WITH TOP PROTECTION',run_dir/'03-protected-outfit.png')]
    board=Image.new('RGB',(1200,530),'#f5f5f0');draw=ImageDraw.Draw(board)
    for i,(label,path) in enumerate(pictures):
        picture=ImageOps.contain(Image.open(path).convert('RGB'),(292,490));board.paste(picture,(i*300+(300-picture.width)//2,30+(490-picture.height)//2));draw.text((i*300+5,8),label,fill='black')
    board.save(dest/'comparison.jpg',quality=92)
    (dest/'index.html').write_text('\n'.join(body),encoding='utf-8')
    with zipfile.ZipFile(ROOT/'dist/masked-outfit-results.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dest.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(dest.parent))
    print(dest/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_dir',type=Path);build(parser.parse_args().run_dir)
