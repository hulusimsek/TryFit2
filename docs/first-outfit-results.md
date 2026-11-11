# İlk gerçek kombin denemesi

## Sonuç

FASHN VTON v1.5 yerel RTX 4060 Ti 8 GB üzerinde gerçekten çalıştırıldı. Kullanıcının gönderdiği iki ürün görseli kullanıldı. İki aktarım sırası ve üst kıyafet için üç ek ayar denendi. **Kombin kalite testi başarısız:** kapüşonlu üst, ürünün yaka/kapüşon/cep ve kesim özellikleri korunarak aktarılamadı.

Bu bir model çalıştırma kanıtıdır; ürünün doğru aktarımı veya uygulamanın hazır olduğu iddiası değildir. On ürünlük geniş test henüz yapılmadı.

## Girdiler

- Profil: kullanıcıya göre değişen boy/kilo alanlarında ilk deneme 175 cm, 65 kg.
- Hedef: built-in image_gen ile oluşturulmuş sentetik yetişkin manken. Fotoğraftaki bedenin ölçüleri doğrulanmış değildir; boy/kilodan fiziksel vücut modeli çıkarılmadı. Prompt ve kaynak [burada](avatar-baseline.md).
- Üst: kullanıcının gönderdiği lacivert kapüşonlu ürün fotoğrafı, `flat-lay`.
- Alt: kullanıcının gönderdiği siyah/beyaz puantiyeli mankenli pijama altı, `model`.
- Orijinaller değiştirilmeden kullanıldı; kaynak ekran görüntülerindeki galeri okları da duruyor.

## Deney

Ana deney: `runs/outfit-20261110T001523Z-3b4bfe/`. Seed 42, 30 adım, guidance 1.5, maskless, tek çıktı, BF16.

| Sıra | Süre (iki inference toplamı) | Görsel inceleme |
|---|---:|---|
| Alt → üst | 71,24 sn | Alt aktarımı makul; üst bluza dönüşüyor, cep kayboluyor, yaka/kesim yanlış. Başarısız. |
| Üst → alt | 71,42 sn | Üstün ilk çıktısında cep kısmen var. Alt aktarımı üstü kısaltıp cep/etek ucunu değiştiriyor; yaka/kapüşon zaten yanlış. Başarısız. |

Her aktarım yaklaşık 35–36 saniye. PyTorch tepe allocated bellek yaklaşık 2,28 GiB, reserved yaklaşık 2,72 GiB. Bunlar toplam GPU/sürücü/ekran belleği değildir. Ölçümler bu tek makine ve bu iki görsel içindir; genel performans garantisi değildir.

Ek deney: `runs/hoodie-refinement-01/`. Aynı başarılı sayılmamış alt ara çıktısı üzerine yalnızca üst yeniden denendi; ilk sonuçlar korundu.

| Ayar | Sonuç |
|---|---|
| 50 adım, seed 42, guidance 2.5, maskless | V yaka/bluz görünümü ve eksik cep devam ediyor. |
| 50 adım, seed 7, guidance 2.5, maskless | Yaka farklılaşıyor; cep, kapüşon ve oversize kesim doğru korunmuyor. |
| 50 adım, seed 42, guidance 2.0, masked | Yaka ve cep sorunu sürüyor; alt kıyafetin görünüşü de değişiyor. |

Hiçbir ek sonuç kıyafet kimliği bakımından başarılı sayılmadı. Bunlar ayar aramasıdır; ana deney başarı oranına eklenmedi.

## Kalite incelemesi

Değerlendirme asistanın görsel incelemesidir; biyometrik veya fiziksel ölçüm değildir.

- Kıyafet kimliği: üst için başarısız. Kapüşon/kanguru cep ve ürün kesimi birlikte korunmuyor.
- Renk/desen: ana renkler ve puantiye motifi aktarılıyor; puantiye yerleşimi birebir aynı değil.
- Kesim: üst kısalıyor veya içeri sokulmuş gibi oluyor; pantolon paça/dökümü de birebir değil.
- Yüz: başlangıç mankenine genel benzerlik korunuyor; çözünürlük düşüyor ve ince detaylar değişiyor.
- Vücut: genel poz/siluet benzer. Gizli bedenin veya 175/65 ölçülerinin korunması bu deneyle doğrulanamaz.
- Kol/el: belirgin ek uzuv görülmedi; el/parmak detayları yumuşuyor.
- Kumaş: görsel olarak makul ışık/kırışıklık var; gerçek ürün kumaşının fiziksel karşılığı doğrulanmadı.
- Kaynak poz: kaynak kişinin pozu doğrudan kopyalanmamış; hedefin önden duruşu genel olarak korunuyor.

## Tekrar çalıştırma ve sınırlar

Proje `.venv` ortamında CUDA PyTorch 2.6.0+cu126, torchvision 0.21.0+cu126, transformers 4.49.0, onnxruntime-gpu 1.22.0, fashn-human-parser 0.1.1 kullanıldı. Tam paket listeleri run klasörlerinde. Kaynak commit ve model revision/hash bilgileri `run.json` ve `model-provenance.json` içinde.

Poz ve parser CPU'da, asıl VTON GPU'da. CFG dalları bellek için sırayla çalışıyor; upstream batched CFG ile dal semantiği eşdeğerlik testi geçti. Model ağırlıkları/çözünürlük değiştirilmedi. Üretim sırasında ağ ve uzaktaki inference servisleri kullanılmadı.

19 yerel kontrol ve `pip check` geçti. Bu kontroller modelin görsel kalitesini onaylamaz.

```powershell
.\.venv\Scripts\python.exe ai-worker/app/outfit.py
.\.venv\Scripts\python.exe ai-worker/app/refine_hoodie.py --parent runs/outfit-20261110T001523Z-3b4bfe
```

Araştırılacak sonraki ayrım: aynı üstün manken üzerinde giyilmiş kaynak fotoğrafıyla tekrar test edilmesi ve ikinci aktarımın ilk parçayı değiştirmesinin sınırlandırılması. Mevcut bulgular, yalnızca daha fazla adım çalıştırmanın problemi çözmediğini gösteriyor. Arayüz/backend geliştirmesi bu kalite sorununu çözmez.
