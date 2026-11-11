# Aynı kombini üç farklı görsel mankende sınama

Üç ayrı sentetik hedefte aynı siyah tişört ve siyah geniş pantolon birlikte çalıştırıldı. Her profilde iki yeni yerel FASHN inference yapıldı; eski kombin görseli yeniden etiketlenmedi. **İnce ve orta görünüm için önizleme kullanılabilir görünüyor; dolgun profilde ayak bölgesi hatası var.** Bu, asistanın görsel ön incelemesidir; genel kalite kapısı veya fiziksel beden uyumu sonucu değildir. Eski on ürünlük 7/10 ön sonuç değişmedi.

| Görsel profil | Yalnızca örnek etiket | Görsel gözlem |
|---|---|---|
| İnce | 165 cm / 55 kg | İnce görünüm, siyah tişört ve pantolon birlikte korunuyor; bel açılmıyor. Tişört etek formu ve bel ayrıntıları değişiyor. |
| Orta | 175 cm / 65 kg | Önceki kombin tekrar üretildi; yeni ham PNG önceki kontrolle byte düzeyinde aynı. İki siyah parça arasında düşük kontrast ve zayıf bel ayrıntısı var. |
| Dolgun | 185 cm / 90 kg | Üst kol, bel ve kalçanın daha dolgun görünümü gözle seçiliyor; ölçülmüş koruma iddiası değildir. Pantolon aşamasında ayaklar siyaha dönüşüyor/kapanıyor. Başarılı uçtan uca aktarım sayılmadı. |

## Ne geliştirildi, ne geliştirilmedi?

Gerçekten farklı üç hedef görüntüsü ve profil kayıtları kullanılır. `avatar_suite.py` üç farklı dosyanın SHA256 değerini, profil kimliklerini, pozitif sonlu örnek sayıları ve `measured=false` koşulunu doğrular. Aynı mankeni üç farklı sayı etiketiyle kullanmak reddedilir. Her profil kendi başlangıç görüntüsünden başlatılır; bir profil diğerinin çıktısını kullanmaz. Model tek kez yüklenir, kaynak kıyafet maskesi her parçanın RGB SHA256'sıyla eşleştirilir.

**Sayısal boy/kilodan vücut şekli hesaplayan bir model henüz yoktur.** Etiketler yalnızca deney kayıtlarıdır; üretim promptları da rakamları beden ölçüsüne dönüştürmez, ince/dolgun görünümü tarif eder. Kamera ölçeği fiziksel boy karşılaştırması için kalibre edilmedi. Ürün beden ölçüsü, boyu veya kumaş mekaniği alınmadı: aynı ürün fotoğrafının aktarılması, aynı fiziksel beden kıyafetin farklı vücutlarda gerçek sıkılık/boluk simülasyonu değildir. Beden tavsiyesi üretilmez.

## Başlangıç görüntüleri ve tam promptlar

Başlangıç mankenleri built-in **image_gen.imagegen** ile üretildi/düzenlendi; CLI veya ücretli API anahtarı kullanılmadı. Yeni iki görsel için eski sentetik manken kimlik/poz/kıyafet referansı verildi. Yalnızca gri tişörtlü, gri leggingli nötr hedefler üretildi; kullanıcı ürünleri bu araca verilmedi ve siyah kombin çizdirilmedi. Ürünler yerel VTON ile eklendi. Yüz/ışık/pozda küçük üretim farkları olabilir; bu nedenle yalnızca vücut değişkeninin izole edildiği iddia edilmez.

- İnce hedef: `data/avatar-profiles/slender.png`.
- Orta hedef: değiştirilmemiş `data/first-outfit/avatar-baseline.png`.
- Dolgun hedef: `data/avatar-profiles/fuller.png`.
- Yeni iki görsel için **kullanılan tam prompt seti**: `evaluation/annotations/avatar-profile-generation.json`.
- Orta hedefin eski tam promptu: `docs/avatar-baseline.md`.
- Profil ve SHA256 kayıtları: `evaluation/manifests/avatar-profiles.json`.

## Gerçek inference ve sonuçlar

Koşu: `runs/avatar-suite-20261110T104433Z-433c41`. İnce hedefte iki aşama toplam 75.50 sn, orta hedefte 70.70 sn, dolgun hedefte 70.02 sn sürdü. Altı yeni inference aşamasının toplamı 216.22 sn. Ayarlar aynı: seed 42, 30 adım, guidance 1.5, BF16, kaynak pozları orijinal fotoğraflardan ve aynı araştırmacı destekli SAM kaynak maskeleri. Genel görüntü üretimi sürelerine manken oluşturma/model yükleme dahil değildir.

İnce koşu: `runs/protected-outfit-8af482a6`; orta: `runs/protected-outfit-a574f9b7`; dolgun: `runs/protected-outfit-423bd670`. Her birinde `01-top.png`, ham `02-bottom-raw.png` ve açıkça belirtilen üst-koruma kompoziti `03-protected-outfit.png` saklandı. Ham ikinci görüntü ana önizlemedir. Üst-koruma maskesi iç/dış piksel koruma testlerini geçti; buna rağmen tişört kenarında ince kontur oluşabilir. Bu kontroller görsel maske doğruluğu veya gerçek beden eşleşmesi kanıtı değildir.

Yeni orta profilin ham çıktı SHA256 değeri `e0fab6a845ffd2015ae5dada94dddb614455dc6da950cb808c1d3bd6858b1947` olup önceki `protected-outfit-aa50fe41/02-bottom-raw.png` ile aynıdır. Bu kontrol, orta çıktının yeniden üretildiğini ve aynı ayarların tekrarlandığını destekler; diğer iki profilin genelleme başarısını kanıtlamaz.

## Ayak koruma denemesi: kabul edilmedi

Dolgun profildeki siyah ayak bölgesi görüldükten sonra üç profile de aynı ek işlem uygulandı. Başlangıç hedefindeki ayak etiketi (insan ayrıştırıcı sınıf 15) üç piksellik yumuşak sınırla ham çıktıya geri kondu. Sonuçlar `04-feet-preserved.png`, maske ve JSON kaydı olarak saklandı. İç ayak piksellerinin orijinal hedefle, maske dışındaki piksellerin ham VTON ile birebir eşleşmesi kontrol edildi; üçünde de maksimum hata 0 oldu.

**Bu işlem pantolon/ayak sınırında kesik izleri bıraktı; tamamlanmış düzeltme olarak kabul edilmedi ve ana önizlemeye alınmadı.** Piksel kopyalamanın doğru çalışması doğal örtüşme üretildiği anlamına gelmez. Ham hatalı sonuç ve reddedilmiş kompozit raporda açıkça gösterilir. `preserve_avatar_feet.py` ayrı deney aracıdır; varsayılan modele dahil değildir.

## Tekrar ve doğrulama

```powershell
# Proje içi HF_HOME ile offline çalışma ortamında:
./.venv/Scripts/python.exe ai-worker/app/avatar_suite.py
./.venv/Scripts/python.exe ai-worker/app/preserve_avatar_feet.py runs/avatar-suite-20261110T104433Z-433c41
./.venv/Scripts/python.exe scripts/build_avatar_suite_report.py runs/avatar-suite-20261110T104433Z-433c41
```

36 yerel kontrol çalıştı; CatVTON ortamına özel bir kontrol bu ortamda atlandı. Yeni kontroller gerçek farklı hedef dosyalarını zorunlu kılar; değiştirilmiş hedefi ve sahte ölçülmüş-beden iddiasını reddeder. Bunlar AI kalite testleri değildir. Kaynak maskeleri araştırmacı tarafından seçilir ve insan ayrıştırıcının araştırma lisansı kısıtı sürer. Tüketici arayüzü veya otomatik kullanıcı vücut üretimi bu aşamada geliştirilmedi.

[Üç kombin görseli](../dist/avatar-suite/three-outfits.jpg) · [Önce/sonra](../dist/avatar-suite/before-after.jpg) · [Ham ve tüm kompozitlerle rapor](../dist/avatar-suite/index.html) · [Taşınabilir ZIP](../dist/avatar-suite-results.zip).
