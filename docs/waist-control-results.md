# Etek tokası kontrolü ve açık gövde koruması

11 Kasım 2026. **Alt parça eklenirken açık karın bölgesinin kıyafetle kapatılması düzeltildi. Eteğin tokası hâlâ eksik.** Bu ayrım gerçek FASHN üretimleriyle kontrol edildi; toka sorunu kapatılmadı ve genel 7/10 oranı değiştirilmedi.

## Yapılan çalışma

- Aynı gerçek etek kaynağı/SAM maskesi, seed 42, 30 adım ve guidance 1.5 ile uzun üst ve belin göründüğü kısa üst kontrolü çalıştırıldı: `runs/skirt-waist-d747c818`. Kısa üstte de toka çıkmadı; model açık karın bölgesini yüksek bir bel bandıyla kapattı. Sorun yalnız üst kıyafetin örtmesi değildir.
- Aynı kısa hedefte kaynak maskesinden ayrılan tam kadraj ve yakın kadraj ayrıca üretildi: `runs/skirt-waist-b9aa563d`. Tokayı geri getirmedi. Bu iki kaynak hazırlığı araştırma seçeneğidir, yerel ekranın varsayılanına alınmadı. Mankenli kaynağın cutout'unu flat-lay dalında kullanmak gerçek düz ürün fotoğrafı değildir; kaynak pozu ve maskeleme yolu da değişir. Tam/ yakın cutout karşılaştırmasında ise yalnız kadraj değişir.
- Koruma maskesinde `torso=16` etiketi eksikti. Üst gövdenin açık ten bölgesi korumaya eklendi; alt kıyafet/bacak etiketleri korunmaya alınmadı. Aynı iki kontrol yeniden gerçek modelde üretildi: `runs/skirt-waist-084546e8`. Açık karın bölgesi korundu; toka yine gelmedi. Toplam altı yeni araştırma üretimi tamamlandı.

Kısa hedefin aynı 1.506 karın iç bölge pikselinde referansa göre ortalama kanal farkı **36,40→0,07** (0–255 ölçeği). Bu, referans bölge koruma ölçümüdür; ürün doğruluğu veya bağımsız kalite puanı değildir. Kaynak/hedef/çıktı hash'leri doğrulandı. [Önce/sonra görseli](../runs/skirt-waist-084546e8/torso-before-after.jpg), [sayısal kayıt](../runs/skirt-waist-084546e8/midriff-review.json).

## Sentetik kontrolün kökeni

`data/waist-control/short-top.png`, built-in `image_gen` ile mevcut sentetik hedefin kısa düz gri üst varyantı olarak üretildi. Etek, kemer veya toka referansı verilmedi; bu bir try-on sonucu değildir ve yerel profil kataloğuna eklenmedi. Görsel düzenleme istenen üst dışında pikselleri de değiştirebilir; uzun/kısa hedef farkı tam kontrollü tek değişken sayılmaz. Gövde düzeltmesinin önce/sonra karşılaştırması ise aynı kısa hedef dosyasını kullanır.

Tam prompt, hedef/çıktı yolları ve SHA-256 değerleri [üretim kaydında](../evaluation/annotations/waist-control-generation.json). Orijinal hedef ve başarısız üretimler korundu.

Tekrar: proje sanal ortamı, mevcut ağırlıklar/girdiler ve proje içi çevrimdışı HF önbelleğiyle:

```powershell
.\.venv\Scripts\python.exe ai-worker/app/skirt_waist_probe.py
.\.venv\Scripts\python.exe ai-worker/app/skirt_waist_probe.py --source-framing
```

Güncel kod gövde korumasını içerir; ilk koşuların eski davranışı kod hash'leri ve saklanan çıktılarda kayıtlıdır. 52 Python testinden 51'i geçti; CatVTON ortamına özel 1 test atlandı. .NET derlemesi 0 hata/uyarı. Yeni testler açık gövde korumasını, alt bölgenin serbest kalmasını ve cutout'un kaynak piksellerini değiştirmemesini kontrol eder.

Mevcut orta profil + bluz + etek akışı API'den yeni kodla tekrar üretildi: iş `95d9ec6c-024b-40d3-acd3-2cca72574aca`, yaklaşık 88,4 sn. İndirilen PNG HTTP 200; SHA-256 outcome ile aynı (`ba318e77…138d3d4`). Koşu metadata'sında `torso` koruması doğrulandı. Sınırlı görsel incelemede belirgin gerileme görülmedi; toka yine eksik. Kayıt: `runs/skirt-waist-084546e8/integration.json`; üretim: `runs/protected-outfit-19ded10e`.

Sonraki mantıklı adım: aynı eteğin alternatif gerçek kaynak fotoğrafıyla kemer/toka aktarımını karşılaştırmak; gövde koruması açıkken ayrıntı kaybını ayrı değerlendirmek.

## Değişen dosyalar

- `ai-worker/app/upper_preservation.py`: açık torso koruması.
- `ai-worker/app/local_job.py`: korunan bölgeler kaydına torso eklenmesi.
- `ai-worker/app/masked_outfit.py`: varsayılan kapalı, doğrulanmış kaynak maskeli cutout araştırma seçeneği.
- `ai-worker/app/skirt_waist_probe.py`: yeni gerçek üretim/karşılaştırma aracı.
- `ai-worker/tests/test_upper_preservation.py`: torso regresyon kontrolü.
- `ai-worker/tests/test_masked_outfit.py`: cutout piksel/maske ve opt-in kontrolleri.
- `evaluation/annotations/waist-control-generation.json`: sentetik kontrolün prompt/provenans kaydı.
- `docs/local-app.md`, `docs/waist-control-results.md`, `docs/progress.md`: yöntem, bulgular ve kısa ilerleme.
- Git dışındaki yeni hedef `data/waist-control/short-top.png`; deneyler/görsel raporlar `runs/skirt-waist-*` altında.
