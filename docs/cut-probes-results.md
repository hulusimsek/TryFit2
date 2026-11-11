# Üç zor ürün için kesim ve duruş denemeleri

Önceki on ürünlük SAM maskeli koşuda başarısız kalan lacivert oversize hoodie, kot ceket ve kahverengi fermuarlı üst aynı hedef üzerinde tekrar sınandı. Önceki `runs/20261110T095148Z-cf9135a6` koşusu ve 7/10 ön değerlendirme değiştirilmedi.

## Sonuç

**Dokuz yeni üretimin hiçbiri mevcut kabul eşiğini geçmedi. Genel ön sonuç 7/10 olarak kaldı.** Bunlar asistanın görsel ön değerlendirmeleridir. Önceki sonuçlar ve olumsuz çıktılar korunur; başarılı örnek seçimiyle oran artırılmadı. Bu bulgu bütün olası ayarların etkisiz olduğunu kanıtlamaz; sınırlandırılmış bu aramanın üç hatayı çözmediğini gösterir.

| Varyant | Hoodie | Kot ceket | Fermuarlı üst |
|---|---|---|---|
| Kaynak pozu boş | Omuz/kollar ve cep bozuldu | Kollar uzadı; manşet, cep ve ön kapama değişti | Açık bol üst dar ve kapalı gövdeye dönüştü |
| Cutout/flat-lay | Benzer kol ve cep bozulması | Benzer detay/kesim kaybı | Benzer kapalı ve dar gövde |
| 50 adım / guidance 2.5 | Bol kesim ve boy sorunu sürüyor | Kol boyu düzelmedi; kol ucunda kumaş çıkıntısı | Kapüşon/baskı belirginleşti; açık fermuar korunmadı |

Kaynak pozu maskeli mankenli kıyafetlerin duruşunu uyarlamak için önemli görünüyor; bu üç örnekte kaldırılması kaliteyi düşürdü. Daha fazla adım/guidance tek başına belirgin kesim hatalarını çözmedi. Bu varyantlar varsayılan pipeline'a alınmadı; kaynak pozunu koruyan 30 adımlık mevcut yöntem varsayılan kaldı. Sonraki karşılaştırmada ikinci model veya daha uygun kaynak çekimlerinin etkisini sınamak, aynı küçük ayar aramasını büyütmekten daha bilgilendirici olabilir.

[Bütün çıktılarla çevrimdışı rapor](../dist/cut-probes/index.html) · [Taşınabilir ZIP](../dist/cut-probes-results.zip). 29 yerel kontrol geçti. Yeni kontrol, hedef pozunun korunmasını ve kaynak-poz ablation durumunun hata sonrasında temizlenmesini sınar. Görsel kaliteyi test kodu belirlemez.

## Varyantlar ve kontrol edilen değişkenler

1. **Kaynak pozu boş:** Orijinal kaynak fotoğrafı, SAM maskesi, kategori, hedef pozu, seed 42, 30 adım ve guidance 1.5 korunur. Yalnızca kaynak DWPose sonucu upstream boş pozuyla değiştirilir. Hedefin pozu ilk çağrıda aynen hesaplanır. Çağrı sırası doğrulanır ve durum her inference sonunda temizlenir.
2. **Cutout/flat-lay dalı:** Aynı SAM maskesi orijinal fotoğrafa uygulanıp gri zeminli kesilmiş görsel, flat-lay parametresiyle işlenir. Bu gerçek düz serilmiş ürün fotoğrafı değildir. Kaynak pozu boş olur; maskeleme ön küçültmeden önce yapılır. Kaynak kod incelemesi, modelde ayrı fotoğraf-türü embedding girdisi bulunmadığını gösterdi. Dolayısıyla ilk iki varyant büyük ölçüde aynı girdileri üretir; bağımsız iki çözüm kanıtı sayılmaz. İlk çalışma metadata'sındaki hatalı embedding ifadesi açıklamalı olarak düzeltildi.
3. **Daha fazla adım ve guidance:** Orijinal kaynak pozu ve SAM maskesi korunur. Seed aynı kalır; adım 30'dan 50'ye, guidance 1.5'ten 2.5'e çıkarılır. Bu, iki parametrenin etkisini ayrı ayrı ölçen deney değildir; sınırlandırılmış bir kalite ayarı karşılaştırmasıdır.

Kod kaynağı: sabitlenmiş FASHN `pipeline.py` dosyasında `garment_photo_type` yalnızca kaynak maskelemesi ve kaynak pozunu etkiler. Model kategori girdisi bundan ayrıdır. Kaynak kodda veya ağırlıklarda değişiklik yapılmadı.

## Yeniden çalıştırma

```powershell
./.venv/Scripts/python.exe ai-worker/app/masked_benchmark.py --case oversize-hoodie --extraction runs/source-extraction-oversize-hoodie-refined --case denim-jacket --extraction runs/source-extraction-denim-jacket-refined --case hooded-sweatshirt --extraction runs/source-extraction-hooded-sweatshirt-refined --disable-source-pose
./.venv/Scripts/python.exe ai-worker/app/cutout_probe.py
./.venv/Scripts/python.exe ai-worker/app/masked_benchmark.py --case oversize-hoodie --extraction runs/source-extraction-oversize-hoodie-refined --case denim-jacket --extraction runs/source-extraction-denim-jacket-refined --case hooded-sweatshirt --extraction runs/source-extraction-hooded-sweatshirt-refined --steps 50 --guidance 2.5
```

Kaynak pozu boş koşusu: `runs/20261110T100205Z-23a0736a`.
Cutout dalı koşusu: `runs/20261110T100428Z-a3808c72`.
50 adım / guidance 2.5 koşusu: `runs/20261110T100728Z-b4028610`.

Üç ürünlük alt kümeler genel kalite kapısını geçiremez; evaluator bu nedenle `pending` üretir. Deneme başına başarı sayısı ve başarısızlıklar ayrı puanlanır. Farklı ayarlardan en iyi çıktıları seçip eski 7/10 oranına eklemek, aynı yöntemle yapılmış yeni on ürünlük test yerine geçmez.

## Sonraki karşılaştırma için aday

Bu ayar aramasını sınırsız büyütmek yerine aynı zor örnekleri ikinci bir modelle karşılaştırmak daha bilgilendirici olabilir. [CatVTON resmî deposu](https://github.com/Zheng-Chong/CatVTON) 1024×768 inference için yaklaşık 8 GB GPU belleği bildirir; bu makinede henüz denenmedi, sığacağı veya daha doğru sonuç vereceği garanti edilmez. Kod ve ağırlıklar CC BY-NC-SA 4.0 altında yalnızca ticari olmayan kullanıma açıktır. Bu nedenle ancak araştırma karşılaştırma adayıdır; Trendyol kullanıcılarına sunulacak ticari ürün için lisans çözümü olarak önerilmez. Bu turda CatVTON indirilmedi ve çalıştırılmadı.
