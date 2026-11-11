# Aynı eteğin alternatif kaynak fotoğrafları

11 Kasım 2026. **İki alternatif galeri fotoğrafı toka kaybını çözmedi.** Başarılı kaynak seçilmedi, yerel katalog değiştirilmedi; genel kalite oranı yeniden ölçülmedi.

[Aynı ürün sayfasındaki](https://www.trendyol.com/swist/siyah-full-pileli-kemerli-astar-sortlu-kadin-mini-etek-p-811422352) dört alternatif fotoğraf indirildi. Ön görünüşlü 3 ve 4 numaralı kareler üretimden önce seçildi. Eteğin elle kaldırıldığı 5 ve arka görünüşlü 6 numara, normal kesim ve toka karşılaştırmasına uygun olmadıkları için dışarıda bırakıldı. Aynı ilandaki fotoğraflar oldukları doğrulandı; fotoğraf kökenleri bağımsız doğrulanmış değildir.

İki seçili kaynak için araştırmacı noktalarıyla SAM2.1 maskeleri çıkarıldı. Maskelerde toka ve etek mevcut; el, ten, bluz ve çanta ayrılmış olarak görsel kontrol edildi. Bu otomatik ürün ayırma değildir. Kaynak URL/hash kayıtları `data/skirt-gallery-20261111/sources.json`, maskeler `runs/source-extraction-skirt-gallery-{3,4}-refined/` altındadır.

## Gerçek üretim karşılaştırması

Üç kaynak aynı sentetik kısa üst hedefiyle, aynı seed 42 / 30 adım / guidance 1.5 / maskeli alt ve gövde koruması açık ayarlarla üretildi. Önceki hedef değiştirilmedi; yeni imagegen kullanımı yoktur. Kaynak fotoğrafıyla birlikte kaynak pozu, kadraj, çözünürlük ve maske de değişir; bu yalnız poz etkisini ölçen bir deney değildir.

| Kaynak | Süre | Sınırlı asistan görsel gözlemi |
| --- | --- | --- |
| Önceki fotoğraf | 39,57 sn | Düz bel bandı; toka yok. Çıktı, önceki `skirt-waist-084546e8/short-top.png` ile SHA-256 düzeyinde aynı. |
| Galeri 3 | 39,39 sn | Pileli etek üretildi, toka yok. |
| Galeri 4 | 39,52 sn | Pileli etek üretildi, toka yok. |

Koşu: `runs/skirt-gallery-910be7db`. Kaynak, hedef, kod, maske ve çıktı hash'leri kaydedildi; üç çıktı hash'i doğrulandı. [Tam karşılaştırma](../runs/skirt-gallery-910be7db/comparison.jpg), [ayrı görsel inceleme kaydı](../runs/skirt-gallery-910be7db/review.json). Bu gözlemler genel kalite kapısı veya bağımsız kullanıcı değerlendirmesi değildir; mevcut 7/10 oranına eklenmez.

Araç başka ürünün fotoğrafını, eksik başlangıç kaynağını, değiştirilmiş dosyayı, proje dışı yolu ve aynı dosyanın farklı kimliklerle tekrar sayılmasını reddeder. 56 Python testi: 55 geçti, ayrı CatVTON ortamı isteyen 1 test atlandı. Son kaynak doğrulama değişikliği için ilgili 4 test ayrıca geçti. .NET derlemesi: 0 hata/uyarı.

Mevcut ağırlıklar, görseller, kaynak maskeleri ve proje içi çevrimdışı HF önbelleğiyle tekrar:

```powershell
.\.venv\Scripts\python.exe ai-worker/app/skirt_gallery_probe.py
```

Sonraki mantıklı adım: aynı etek ve kısa üst hedefiyle mevcut ikinci modeli sınırlı karşılaştırmak. Bu üç kaynakta sonuç alınamaması, bütün kaynakların veya modellerin başarısız olacağını kanıtlamaz. İkinci modelin araştırma lisansı ve ayrı ortam sınırları korunmalıdır.

## Bu turda değişen 7 kod/belge dosyası

- `ai-worker/app/skirt_gallery_probe.py`: sabit kaynak seçimiyle gerçek üretim aracı.
- `ai-worker/tests/test_skirt_gallery_probe.py`: kaynak/ürün kimliği ve dosya doğrulama kontrolleri.
- `evaluation/manifests/skirt-gallery-comparison.json`: üretimden önce seçilen üç kaynak ve dışlama gerekçeleri.
- `evaluation/annotations/skirt-gallery-3.sam2.json`.
- `evaluation/annotations/skirt-gallery-4.sam2.json`.
- `docs/skirt-gallery-results.md`.
- `docs/progress.md`.

Yeni görseller ve indirme kaydı `data/skirt-gallery-20261111/`, maskeler ve üretimler yukarıdaki `runs/` dizinlerinde Git dışında tutulur. Önceki kaynaklar/başarısız çıktılar korunmuştur.
