# Ayak hatasını girdide maskeleme ile sınama

**Aynı üç profilde ayaklar yeni ham FASHN üretiminde görünür kaldı; dolgun profildeki önceki siyah/kapanmış ayak bölgesi bu örnekte düzeldi.** Görüntülere sonradan ayak veya üst kıyafet pikselleri yapıştırılmadı. Bu, asistanın görsel ön incelemesidir; genel başarı veya ölçülü beden uyumu kanıtı değildir. Paça boyu ve üst etek ucundaki değişiklikler devam eder.

Önceki üç profil testi `runs/avatar-suite-20261110T104433Z-433c41` değiştirilmedi. Her profilin aynı `01-top.png` çıktısı kullanıldı. Yalnızca pantolon inference aşamasında `segmentation_free=True` yerine **False** seçildi. Aynı gerçek kaynak fotoğrafı, SAM kıyafet maskesi, kaynak/ hedef pozu, seed 42, 30 adım ve guidance 1.5 korundu. Üç yeni pantolon inference yapıldı; ilk tişört aşaması veya mankenler yeniden üretilmedi.

## Neden bu kontrol yapıldı?

Önceki maskesiz hedefli üretim ayaklar görünürken onları değiştirebiliyordu. Sonradan ayak piksellerini geri koymak ise yeni pantolonun sınırını kesiyordu; o kompozit denemesi başarılı sayılmadı. Yeni testte upstream FASHN hedef hazırlığı kıyafet/alt gövde alanını gri maskeleyerek ayak bağlamının çoğunu girdide bırakır. Sonuç bütünüyle modelin çıktısıdır; post-composite uygulanmaz.

Upstream hazırlık tüm ayak piksellerini kesin korumaz: buffer genişlemesi bazı sınır piksellerine dokunur. Bu sayı gerçek ayrıştırıcı etiketleri üzerinden ayrıca kaydedildi. Maskeli girdi PNG'leri raporda görünür.

| Profil | Ayak etiketli piksel | Hedef hazırlığında değişen | Inference süresi | Görsel gözlem |
|---|---:|---:|---:|---|
| İnce | 4131 | 128 | 36.57 sn | Ayaklar görünür; paça daha kısa/düz, tişört etek formu değişiyor. |
| Orta | 4572 | 143 | 35.54 sn | Ayaklar görünür; paça yığılması azaldı, bel/düğme ayrıntısı zayıf. |
| Dolgun | 4743 | 144 | 35.89 sn | Önceki siyah ayak bölgesi artık yok; daha dolgun görünüm seçiliyor. Paça ve üst boyu değişiyor. |

Üç yeni inference toplam 108.00 sn sürdü. PyTorch peak allocated 2.276 GiB idi; sürücü ve masaüstü belleği bu değere dahil değildir. Kaynak/çıktı SHA256'ları ve checkpoint hash'leri doğrulandı. Bütün olumsuz önceki görüntüler korunur.

## Kapsam ve sınırlar

- Paçanın kısalması otomatik olarak doğru kıyafet boyu sayılmaz; ürünün gerçek ölçüsü ve bedeni alınmadı.
- Alt bölüm maskelenirken tişört etek ucunun görünümü de değişebilir. Üç profilde görsel olarak belirgin yüz/anatomi bozulması görülmedi; bağımsız panel veya sayısal vücut ölçümü yapılmadı.
- Bunlar ince/orta/dolgun hazır sentetik görsel profillerdir. Boy/kilo etiketlerinden vücut hesaplayan sürekli bir model yoktur.
- Aynı pantolon fotoğrafını üç hedefe uygulamak aynı fiziksel beden kıyafetin oturuşunu simüle etmek değildir.
- Kaynak maskeleri araştırmacı tarafından seçildi. İnsan ayrıştırıcının araştırma lisansı kısıtı sürer.
- Genel on ürünlük **7/10** ön sonucu değişmedi. Varsayılan pipeline değiştirilmedi; yeni yöntem deneysel bir seçimdir.

## Uygulama ve tekrar

`SourceMaskParser` varsayılan olarak maskesiz hedef davranışını korur. Yeni maskeli hedef kullanımı açık `allow_masked_target=True` gerektirir. İlk hedef ayrıştırma çağrısı gerçek parser'dan gelir; boyut/etiket aralığı veya boş sonuç geçersizse işlem reddedilir. İkinci çağrı yalnızca kaynak kıyafet maskesini uygular. Durum hata sonrasında temizlenir.

`protect_outfit.py` artık üst ve alt aşama ayarlarını ayrı kaydeder. Yeni `avatar_suite.py --masked-bottom` seçeneği üst aşamayı aynı bırakıp yalnızca alt aşamayı maskeli hedefle çalıştırır. Flag verilmezse eski davranış sürer. Bu seçenek tam altı-aşamalı koşu için eklendi; bu turda onun yerine değişmemiş ilk aşamalar yeniden kullanılarak yalnızca üç kontrollü alt-aşama inference çalıştırıldı.

Asıl koşu: `runs/feet-input-20261110T105726Z-bdcbee`.

```powershell
# Proje içi HF_HOME ve offline çalışma değişkenleri ile:
./.venv/Scripts/python.exe ai-worker/app/feet_input_probe.py runs/avatar-suite-20261110T104433Z-433c41
# Aynı protokolü gelecekte üstten başlayarak tüm profillere uygulamak için:
./.venv/Scripts/python.exe ai-worker/app/avatar_suite.py --masked-bottom
./.venv/Scripts/python.exe scripts/build_feet_input_report.py runs/feet-input-20261110T105726Z-bdcbee
```

38 yerel kontrol çalıştı; CatVTON'a özel bir kontrol kendi ortamını gerektirdiği için atlandı. Yeni kontroller maskeli hedefte gerçek etiketlerin kullanılmasını, boş ayrıştırmanın reddedilmesini ve üst/alt aşama parametrelerinin gerçek çağrılarla kayıtlarının eşleşmesini doğrular. Bu testler AI görsel kalitesini belirlemez.

[Üç yeni ham kombin](../dist/feet-input/three-outfits.jpg) · [Önce/sonra](../dist/feet-input/before-after.jpg) · [Girdi maskeleri ve bütün sonuçlar](../dist/feet-input/index.html) · [Taşınabilir ZIP](../dist/feet-input-results.zip).
