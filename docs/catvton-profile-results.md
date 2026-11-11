# CatVTON: iki profil ve gerçek kombin kontrolü

11 Kasım 2026. **Bluz + etek kontrolünde gri bel şeridi giderildi ve toka görünür kaldı. Üst/el/ayak için seçilen koruma pikselleri üç hedefte de repaint çıktısında aynen korundu.** Bu, modelin öğrendiği kimlik koruması değil, açık hedef pikseli kopyalamasıdır. Kesim/beden doğruluğu ve genel kalite kapısı doğrulanmadı; yerel FASHN motoru değiştirilmedi.

## Gerçek girdiler ve ilk üç üretim

İnce ve dolgun hazır sentetik hedefler ile gerçek FASHN bluz aşaması (`runs/protected-outfit-19ded10e/01-top.png`) kullanıldı. Bluz yeniden üretilmedi veya imagegen ile çizilmedi; önceki tamamlanmış koşu ve dosya hash'i doğrulandı. Aynı eski etek kaynağı/SAM maskesi, CatVTON ağırlıkları, seed 42, 50 adım, guidance 2.5 ve eta 1.0 korundu. Her hedef için ayrı araştırmacı hedef maskesi çizildi.

İlk seri: `runs/catvton-profile-suite-a33ae897`.

| Hedef | İlk koşu / süre | İlk bulgu |
| --- | --- | --- |
| İnce | `catvton-skirt-1649d300` / 36,93 sn | Etek/toka görünür; ham çıktıda yüz/üst dokusu değişiyor. Yumuşak maske ellere de değiyor. |
| Dolgun | `catvton-skirt-31c365bc` / 37,09 sn | Pile ve kemer zayıf, etek üstünde gri geçiş var. Kabul edilmiş bir ürün doğruluğu sonucu değil. |
| Gerçek bluz aşaması | `catvton-skirt-32168f3c` / 37,25 sn | Kombin oluşuyor; bluz altında eski gri tayt bandı kalıyor. |

Maske bulanıklaştırması dışlanan el/üst sınırlarına tekrar alfa yayıyordu. İlk seride hedefe göre repaint maksimum kanal farkı ellerde 57–128, üstte 31–107 idi. Sayılar 0–255 ölçeğinde referans farkıdır, kalite puanı değildir. Kayıt ve ayrıştırma etiketleri: `runs/catvton-profile-suite-a33ae897/region-review.json`.

## Düzeltme ve üç yeni üretim

`target_inputs`, isteğe bağlı, hedef SHA-256'sına bağlı bir koruma maskesi kabul eder. Düzenleme zarfı bulanıklaştırıldıktan sonra korunan piksellerde **hem sert hem yumuşak alfa sıfırlanır**. Yanlış hedefe bağlı, değiştirilmiş, yanlış boyutlu veya geçersiz maske reddedilir. Maske verilmezse önceki yol sürer.

Koruma maskeleri gerçek FASHN insan ayrıştırıcısının CPU çıktısındaki yüz/saç/üst/kol/el/ayak/torso etiketlerinden hazırlandı. Bu etiketlerin doğru sınıflandırılması ayrıca bir sınırlamadır. Dolgun ve bluz hedeflerinde eski tayt bandını kapsamak için düzenleme zarfı da genişletildi; bu ikisinde iki değişiklik birlikte yapıldığından yalnız birinin etkisi diye yorumlanmaz. İnce hedefte zarf aynı kaldı, yalnız koruma eklendi.

Takip serisi: `runs/catvton-profile-preserved-0b88c788`.

| Hedef | Takip koşusu / süre | Sınırlı görsel gözlem |
| --- | --- | --- |
| İnce | `catvton-skirt-3be42a89` / 36,96 sn | Üst/el/ayak pikselleri korunuyor. Uzun üst kemeri örtüyor; görünmeyen toka başarı sayılmadı. |
| Dolgun | `catvton-skirt-5ff447c9` / 37,10 sn | Gri geçiş yerine siyah pileli etek; kemer/toka uzun üst altında görünmüyor. Kesim hâlâ yaklaşık. |
| Gerçek bluz aşaması | `catvton-skirt-79cdd707` / 36,67 sn | Gri bel şeridi yok, C biçimli toka görünür; ilk aşama bluzu seçilen bölgede aynen korunuyor. |

Toplam altı yeni inference ve on iki ham/repaint PNG'sinin hash'leri doğrulandı. Üç hedefte seçilen 87.264 / 114.084 / 89.895 koruma pikselinde maksimum kanal farkı **0**. Ham çıktı aynı bölgelerde hâlâ değişiyor; repaint kopyalaması AI başarısı olarak sayılmaz. [Doğrulama kaydı](../runs/catvton-profile-preserved-0b88c788/review.json), [üç hedef](../runs/catvton-profile-preserved-0b88c788/three-targets.jpg), [bluz önce/sonra](../runs/catvton-profile-preserved-0b88c788/blouse-before-after.jpg). Panolarda CatVTON'un yalnız boş letterbox kenarları kesildi; asıl PNG'ler değişmedi.

Koruma farkı, hazırlanmış 768×1024 hedef tuvaline karşı ölçülür; orijinal çözünürlükteki PNG ile doğrudan piksel eşitliği iddiası değildir.

## Tekrar ve teknik kontroller

Koruma maskelerini oluşturan araç CPU'da mevcut parser'ı kullanır; farklı mevcut dosyayı ezmez. Bu görevde tekrar çalıştırılarak mevcut üç maske aynı PNG hash'leriyle doğrulandı:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_catvton_preservation.py --annotation evaluation/annotations/slender-lower.catvton.json --annotation evaluation/annotations/fuller-lower.catvton.json --annotation evaluation/annotations/blouse-stage-lower.catvton.json --output-dir runs/catvton-profile-suite-a33ae897
.\.venv-catvton\Scripts\python.exe ai-worker/app/catvton_skirt_probe.py --annotation evaluation/annotations/blouse-stage-lower-preserved.catvton.json --case skirt
```

Diğer hedeflerin tekrarında aynı komutta ilgili `slender-lower-preserved` / `fuller-lower-preserved` anotasyonu kullanılır. Eski koşu/görseller, mevcut yerel ağırlıklar ve proje içi çevrimdışı HF önbelleği gerekir. Yeni ağırlık veya ücretli servis eklenmedi.

Ana ortam: 61 test, 60 geçti, CatVTON'a özel 1 atlandı. CatVTON ortamı: ilgili 9 test geçti. .NET derlemesi: 0 hata/uyarı. Koruma alanında yumuşak alfanın sıfır kalması, diğer alanların düzenlenebilmesi ve maskenin hedef/hash bağı yeni kontrollerle sınandı.

## Kalan sınırlar ve sonraki adım

Bu üç hedef, genel kullanıcı başarısı veya bağımsız kalite değerlendirmesi değildir. Ellerin/üstün yanlış ayrıştırılması, yeni pozlar, paça/etek boyu, bacak oranları ve kumaş fiziği doğrulanmadı. Uzun üst altında görünmeyen kemer için başarı iddiası yoktur. Önceki 7/10 oranı değişmedi. CatVTON ve insan ayrıştırıcısının kayıtlı araştırma lisansı sınırları sürer; ticari dağıtım uygunluğu sağlanmış sayılmaz.

Sonraki mantıklı adım: bu sınırlı etek akışını yerel araştırma ekranında açıkça deneysel ve ayrı bir model seçeneği olarak sunmak; üretim kalitesi veya ticari kullanım iddiası eklememek. Entegrasyonda çalışma anında maske hazırlığı, ayrı Python ortamı, hata/iptal ve ham/repaint kaydı korunmalıdır.

## Bu turda değişen 13 dosya

- `ai-worker/app/catvton_inputs.py`.
- `ai-worker/app/catvton_skirt_probe.py`.
- `ai-worker/tests/test_catvton.py`.
- `ai-worker/tests/test_catvton_skirt.py`.
- `scripts/prepare_catvton_preservation.py`.
- `evaluation/annotations/slender-lower.catvton.json`.
- `evaluation/annotations/fuller-lower.catvton.json`.
- `evaluation/annotations/blouse-stage-lower.catvton.json`.
- `evaluation/annotations/slender-lower-preserved.catvton.json`.
- `evaluation/annotations/fuller-lower-preserved.catvton.json`.
- `evaluation/annotations/blouse-stage-lower-preserved.catvton.json`.
- `docs/catvton-profile-results.md`.
- `docs/progress.md`.

Yeni maskeler, etiketler, ham/repaint üretimler ve kayıtlar belirtilen `runs/` dizinlerinde Git dışında saklanır. Önceki başarısız çıktılar silinmedi.
