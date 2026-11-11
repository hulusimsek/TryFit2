# CatVTON ile etek ayrıntısı karşılaştırması

11 Kasım 2026. **Aynı etekte CatVTON, ilk iki kaynakta görünür gümüş toka üretti. Tek örneklik maske takibinde gri tayt bel kalıntısı da giderildi.** Bu sınırlı asistan görsel ön incelemesidir; tam kıyafet doğruluğu, bağımsız kalite kapısı veya üretim onayı değildir. Yerel uygulamanın FASHN motoru değiştirilmedi.

## Gerçek üretimler

Önceki üç etek kaynağı, aynı SAM maskeleri ve aynı sentetik kısa üst hedefi kullanıldı. CatVTON `mix-48k-1024`, BF16, seed 42, 50 adım, guidance 2.5, eta 1.0 ve 768×1024 tuvalle çalıştı. Kurulu ayrı ortam ve mevcut ağırlıklar kullanıldı; yeni indirme, bağımlılık veya ücretli servis eklenmedi. Model dosyalarının kayıtlı hash'leri doğrulandı.

| Koşu / kaynak | Süre | Görsel gözlem |
| --- | --- | --- |
| `catvton-skirt-3bcec786` / eski kaynak | 40,74 sn | Yaklaşık C biçimli gümüş toka görünür; eski gri tayt bandı kalıyor. |
| Aynı koşu / galeri 3 | 40,47 sn | Gümüş toka görünür; gri bel şeridi sürüyor. |
| Aynı koşu / galeri 4 | 40,33 sn | Kemer var; toka biçimi/rengi kaynakla uyuşmuyor. |
| `catvton-skirt-6805edd6` / eski kaynak | 39,19 sn | Yalnız hedef maskesinin üst iki köşesi 0.383→0.365 yükseltildi. Gri şerit görünmüyor, gümüş toka görünür kalıyor. Bel çizgisi/örtülme de değişiyor; birebir kaynak kesimi kanıtlanmadı. |

Dört inference ve bunların sekiz ham/repaint PNG'si saklandı. Tüm çıktı hash'leri doğrulandı. Takipte hedef, kaynak, condition, kaynak maskesi ve sampler ayarları aynı; el dışlama çokgenleri ve diğer hedef köşeleri değişmedi. İlk üç sonuç ve başarısız ayrıntılar korundu. [Karşılaştırma](../runs/catvton-skirt-6805edd6/model-comparison.jpg), [inceleme ve doğrulama kaydı](../runs/catvton-skirt-6805edd6/review.json). Karşılaştırma panosunda yalnız CatVTON tuvalinin boş letterbox kenarları gösterim için kesildi; orijinal PNG'ler değişmedi.

## Maskeler ve sınırlar

Alt gövde maskesi araştırmacı tarafından çizildi. Önizlemede parmakların bir kısmı zarf içinde kaldığı için üretimden önce el dışlama çokgenleri eklendi. Eski anotasyonların davranışı değişmez; yeni dışlama alanı isteğe bağlıdır. İlk maske üç kaynakta sabittir; bel takibi ayrı anotasyondur.

CatVTON kaynağı beyaz zemindeki SAM cutout'u ve farklı çözünürlük/sampler/maske ile işler. Bu nedenle fark yalnız ağ mimarisine bağlanamaz. Ham sonuç ile resmî `repaint_result` sonucu ayrı kaydedilir. Repaint maske dışını orijinal hedeften kopyalar: takipte sıfır maske bölgesinde maksimum fark 0, ham sonuçta aynı bölgenin ortalama farkı yaklaşık 4,31/255'tir. Bu, repaint kimlik korumasının modelin öğrendiği bir yetenek olmadığını doğrular.

Toka görünmesi eteğin tamamının doğru aktarıldığı anlamına gelmez. Pile/kesim ve vücut oranları yaklaşık; bağımsız değerlendirme yapılmadı. İlk kaynakta gözlenen daraltılmış bel/karın açıklığı ve ham görüntüde maske dışı değişimler ayrıca değerlendirilmelidir. Önceki üç zor üstteki CatVTON 0/3 ve FASHN 7/10 kayıtları değiştirilmedi; bu yeni etek alt kümesi onlara eklenmedi.

CatVTON için yerel kayıtlardaki CC BY-NC-SA 4.0 araştırma sınırı sürer; ticari dağıtım uygunluğu veya üretim motoru önerisi değildir. [Önceki kurulum ve lisans kaydı](catvton-results.md).

## Kontroller ve tekrar

Ana Python ortamı: 59 test, 58 geçti, CatVTON'a özel 1 test atlandı. Ayrı CatVTON ortamında ilgili 7 testin tamamı geçti; gerçek küçük adapte UNet'in toplu/ardışık eşdeğerliği de doğrulandı. .NET derlemesi 0 hata/uyarı. Yeni el dışlama, kaynak pikseli ve maske kimliği kontrolleri AI kalite puanı üretmez.

Proje içi çevrimdışı HF önbelleği ve mevcut girdiler/ağırlıklarla:

```powershell
.\.venv-catvton\Scripts\python.exe ai-worker/app/catvton_skirt_probe.py
.\.venv-catvton\Scripts\python.exe ai-worker/app/catvton_skirt_probe.py --annotation evaluation/annotations/short-top-lower-waist.catvton.json --case skirt
```

Sonraki mantıklı adım: aynı etek için diğer iki hazır hedefte maske/ham/repaint davranışını ve gerçek üst+alt kombinini kontrol etmek. Araştırma uygulamasına adaptör eklemeden önce bu sınırlı genelleme ve kıyafet koruma kontrolü tamamlanmalıdır.

## Değişen 8 dosya

- `ai-worker/app/catvton_skirt_probe.py`: gerçek ikinci model karşılaştırma aracı.
- `ai-worker/app/catvton_inputs.py`: isteğe bağlı hedef dışlama çokgenleri.
- `ai-worker/tests/test_catvton.py`: dışlama geometrisi kontrolü.
- `ai-worker/tests/test_catvton_skirt.py`: kaynak pikseli ve maske kimliği kontrolleri.
- `evaluation/annotations/short-top-lower.catvton.json`: ilk sabit alt gövde maskesi.
- `evaluation/annotations/short-top-lower-waist.catvton.json`: yalnız bel sınırı takibi.
- `docs/catvton-skirt-results.md`.
- `docs/progress.md`.

Yeni maskeler, condition görselleri, ham/repaint çıktıları, ortam ve model kayıtları belirtilen `runs/` dizinlerinde Git dışında saklanır.
