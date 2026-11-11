# İkinci model: yerel CatVTON karşılaştırması

**CatVTON yerel RTX 4060 Ti 8 GB üzerinde gerçek inference ile çalıştı. Üç zor mankenli kaynakta görsel ön değerlendirme 0/3; önceki FASHN + SAM sonucu 7/10 olarak kaldı.** Asistanın görsel ön değerlendirmesidir; bağımsız insan paneli veya otomatik doğruluk ölçümü değildir. CatVTON varsayılan pipeline yapılmadı.

| Ürün | Gözlem | Ön sonuç |
|---|---|---|
| Lacivert oversize hoodie | Daha rahat hacim ve kol boyu var; göğüste üründe olmayan büyük ten rengi yama oluştu. | Başarısız |
| Kot ceket | Kollar uzadı; crop gövde uzadı, ek panel/etek çizgileri ve değişmiş cepler oluştu. | Başarısız |
| Kahverengi fermuarlı üst | Fermuar tamamen kapandı; baskının şekli ve dağılımı değişti. | Başarısız |

Üç örneğin ortalama gerçek üretim süresi yaklaşık 40 saniye; PyTorch peak allocated 2.389 GiB, reserved yaklaşık 3 GiB. Bir örnekte gözlenen toplam GPU kullanımı 3542 MiB idi; masaüstü ve sürücü kullanımı değişir. Bu sayılar resmi standart kurulumun bellek ihtiyacı değildir; aşağıdaki yerel uyarlamalarla ölçüldü.

## Yöntem ve karşılaştırmanın sınırları

Kaynaklar aynı üç gerçek ürün fotoğrafıdır. Önceden araştırmacı tarafından seçilmiş SAM maskelerinin görünür kumaşı beyaz zemine alınır; yalnızca görünür kumaş sınır kutusuna 12 piksel pay verilerek kesilir. Saç, el ve çanta arkasındaki kumaş yeniden oluşturulmadı. Bu kaynak hazırlığı otomatik ürün seçimi değildir. CatVTON için FASHN'den farklı zorunlu ön hazırlık kullanıldı; karşılaştırma yalnızca ağ mimarisinin etkisini ayırmaz.

Hedef aynı sentetik mankendir. 768×1024 tuvale kırpılmadan yerleştirilir; yüz/ayak kaybı yoktur. Araştırmacının çizdiği üst-gövde zarfı üç örnekte sabittir. `evaluation/annotations/avatar-upper.catvton.json` dosyasında hedef SHA256 ve normalize çokgen saklanır. Bu maske otomatik değildir; farklı hedefler için genelleme gösterilmedi. Boy/kilo ile ölçülü vücut oluşturma veya gerçek beden uyumu sınanmadı.

Model: CatVTON `mix-48k-1024`, BF16, 50 adım, guidance 2.5, seed 42, eta 1.0. PyTorch ve NumPy RNG her örnekte sıfırlanır. Resmî inference akışı kullanılır; kaynak kod değiştirilmez. Yerel subclass yalnızca checkpoint yolları ve bellek yürütmesini uyarlar: yerel VAE, CPU yükleme/BF16 CUDA, UNet'in iki CFG örneğinin ayrı yürütülmesi, VAE 512 örnek / 64 latent tiling ve slicing. Resmî `inference.py` veri kümesi modu gibi safety checker çalıştırılmaz; girdiler yetişkin günlük kıyafet araştırma görselleridir.

Her örnekte **ham ağ çıktısı** ve resmî `repaint_result` uygulanmış **ana çıktı** ayrı dosyalardır. Ana çıktı puanlandı. Repaint maske dışındaki orijinal hedefi geri koyar; maske içinde gerçek inference sonucu kalır. Bu nedenle yüz/alt vücut korunması model yeteneği olarak sunulmaz. Maske dışı kopyalama, kıyafetin doğru üretildiğini kanıtlamaz. Raporda iki sürüm de görünürdür.

Ana koşu: `runs/catvton-20261110T102110Z-f17683`. Ağırlık revision ve SHA256, kaynak/maske/condition hash'leri, hedef dönüşümü, tüm ham çıktılar, süre/bellek ve hata kayıtları `run.json` içindedir. Üç ürünlük alt küme evaluator'da `pending` kalır; genel on ürünlük kapıyı geçiremez.

## Ayrı düz ürün fotoğrafı kontrolleri

Aynı hoodie ürününün gerçek düz serilmiş galeri fotoğrafı ile ek bir koşu yapıldı: `runs/catvton-20261110T102411Z-9351a2`. Kaynakta olmayan yama kayboldu; fakat kapüşon da kaybolup bisiklet yakalı sweatshirt oluştu. İlk hedef maskesinin yaka çevresindeki sınırı olası etkendir.

Yalnızca maskenin yaka çevresindeki sınırı yukarı genişletilerek ikinci kontrol yapıldı: `runs/catvton-20261110T102654Z-d9fe8b`. Yeni maske `evaluation/annotations/avatar-upper-neck.catvton.json` içinde ayrıdır. Gri eski yaka kalıntısı gitti ve kapüşon/yaka geri geldi. Kanguru cep girişleri/şekli ve bol kesim yine yeterince korunmadı; bu örnek de kabul eşiğini geçmedi. Bu maske kontrolü ilk üç üründe tekrar uygulanmadı; ilk 0/3 sonucunun her olası maskede geçerli olduğu iddia edilmez.

İki ek kontrol kaynak ve maske hazırlığına duyarlılığı gösterir. İlk üç mankenli kaynak sonucu ve eski 7/10 oranına eklenmedi. Hiçbir olumsuz çıktı silinmedi. Bu deneyler CatVTON'un tüm ürünler/kurulumlar için başarısız olduğunu kanıtlamaz.

## Kurulum, lisans ve tekrar

[Resmî CatVTON deposu](https://github.com/Zheng-Chong/CatVTON) commit: `7818397f25613beedb3d861a34769f607cfcf3b1`. CatVTON kaynaklarından türetilen yerel başlangıç/inference uyarlaması için aynı CC BY-NC-SA 4.0 koşulları geçerlidir. CatVTON kodu, checkpoint ve demo ticari olmayan kullanıma açıktır; bu çalışma yalnızca araştırma karşılaştırmasıdır. Ticari Trendyol ürünü için dağıtım izni olarak önerilmez. Kaynak lisans vendor deposunda korunmuştur.

Model revision'ları: CatVTON `2969fcf85fe62f2036605716f0b56f0b81d01d79`, resmî uygulamanın işaret ettiği SD inpainting aynası `d260cf3646fe94c6d5d70820b77512f836d7cce2`, SD VAE `31f26fdeee1355a5c34592e401dd41e45d25a493`. Üç büyük dosyanın hash'leri Hub LFS SHA256 değerlerine karşı doğrulandı. İndirme planı ve sonuç `ai-worker/models/catvton/` içinde saklanır; ücretli API çağrısı yoktur.

Ayrı `.venv-catvton` oluşturuldu. Bu ortam kendi diffusers 0.29.2, accelerate 0.31.0, hub 0.25.2, transformers 4.44.2 ve tokenizers 0.19.1 paketlerini kullanır. PyTorch ve ortak paketleri proje içindeki çalışan `.venv/Lib/site-packages` klasörüne işaret eden `.pth` üzerinden okur; FASHN ortamındaki paketler değiştirilmez. Tam kurulum bağımsız taşınabilir venv değildir; ortak ortam yolunu yeniden kurmak gerekir. Sürümler `ai-worker/requirements-catvton-tested.txt` ve her koşunun `pip-freeze.txt` dosyasında kayıtlıdır. xformers, Detectron2 ve DensePose kurulmadı; hedef maskesi araştırmacı tarafından verildi.

```powershell
./.venv/Scripts/python.exe scripts/download_catvton_weights.py
# HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1 ve proje içi HF_HOME ile:
./.venv-catvton/Scripts/python.exe ai-worker/app/catvton_probe.py
./.venv-catvton/Scripts/python.exe ai-worker/app/catvton_probe.py --flatlay-hoodie
./.venv-catvton/Scripts/python.exe ai-worker/app/catvton_probe.py --flatlay-hoodie --annotation evaluation/annotations/avatar-upper-neck.catvton.json
```

Ana ortamda 32 kontrol çalıştı, CatVTON ortamına özel UNet kontrolü orada atlandı. CatVTON ortamındaki dört kontrolün tamamı geçti: gerçek küçük CatVTON-adapte UNet üzerinde toplu/ardışık forward eşdeğerliği, hedef/maske hizası ve tam boyun korunması, seçilen kaynak piksellerinin aynen kalması, geçersiz maskenin reddedilmesi. Bunlar AI görsel kalite testi değildir.

[Tüm ham ve repaint çıktılarıyla çevrimdışı rapor](../dist/catvton-comparison/index.html) · [Taşınabilir ZIP](../dist/catvton-comparison-results.zip).
