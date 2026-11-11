# İkinci parçada üst kıyafeti koruma

11 Kasım 2026: mevcut ürün kaynaklarıyla iki kombinin alt aşaması gerçek modelde yeniden üretildi. Bluzun desen/etek ucu değişimi azaldı. Bu, sınırlı asistan görsel incelemesidir; genel kalite kapısı veya bağımsız değerlendirme değildir. Pantolon kaynağının ürün sayfasında AI üretim etiketi bulunduğu önceki kayıtlarda belirtilir; bu kaynak bağımsız doğrulanmış gerçek fotoğraf sayılmaz.

## Değişiklik

Önceki maskeli alt aşama, görüntünün tamamını yeniden ürettiği için üst parçayı değiştirebiliyordu. Yeni `upper_preservation.py`, üst/kimlik iç bölgelerini her Euler adımında aynı başlangıç gürültüsünden ilk aşama görüntüsüne ilerleyen yörüngeyle sınırlar. Üstün sınırında 864 piksel yükseklikte yaklaşık 6 piksellik yumuşak geçiş alanı serbest bırakılır. Bitmiş sonuca piksel yapıştırılmaz; bu yine de referans piksellerle kısıtlanan bir üretimdir, modelin kendiliğinden öğrendiği bir koruma garantisi değildir.

Yerel işlerde alt aşamada açık; diğer araştırma koşularında varsayılan kapalıdır. Vendor kodu ve model ağırlıkları değiştirilmedi. Kaynak SAM maskeleri ve gerçek hedef ayrıştırması korunur; ayrıştırma geçersizse örnek sonuç yerine hata oluşur.

## Kontrollü karşılaştırma

Aynı kaydedilmiş `01-top.png`, kaynak fotoğrafı/maskesi, seed 42, 30 adım, guidance 1.5 ve maskeli alt ayarı kullanıldı. Yalnız üst koruma kısıtı eklendi. Eski çıktılar korundu.

| Kombin | Eski → yeni korunan bölge ortalama kanal farkı | Görsel gözlem |
| --- | --- | --- |
| Orta profil, çiçekli bluz + etek | 7,49 → 0,13 | Bluzun deseni ve sivrilen etek ucu daha iyi korunuyor; etek üretiliyor. Kaynak eteğin kemer/tokası hâlâ eksik. |
| Dolgun profil, tişört + pantolon | 1,33 → 0,79 | Üst iç bölgesi korunuyor; ayaklar görünür. Pantolonun kısa paçası ve üst sınırındaki değişiklikler sürüyor. |

Farklar 0–255 kanal ölçeğinde, ilk aşama görüntüsüne karşı tam korunan iç bölgelerde ölçülür; yüz, saç, kol ve elleri de içerir. Kıyafet doğruluğu puanı değildir. BF16 hesaplama/PNG dönüşümü küçük fark bırakabilir. Kenar piksellerinin korunması veya gerçek beden uyumu bu ölçümle kanıtlanmaz.

Kanıtlar:

- Yeni başlangıç üretimi: `runs/protected-outfit-d78dd586`; önceki bluz/etek çıktısıyla SHA-256 aynı (`3be4c8fd…aa20ee9e`).
- Bluz/etek karşılaştırması: `runs/upper-preservation-c0f16e36/run.json`, [görsel](../runs/upper-preservation-c0f16e36/0-comparison.jpg). Yeni alt aşama yaklaşık 40,24 sn.
- Tişört/pantolon karşılaştırması: `runs/upper-preservation-44ac6d9e/run.json`, [görsel](../runs/upper-preservation-44ac6d9e/0-comparison.jpg). Başlangıç `runs/protected-outfit-fb56c42d`; yeni alt aşama yaklaşık 40,28 sn.
- Yerel API üzerinden yeni bluz/etek işi `a703be07-55d0-40d1-95ff-63e9ae566843`, yaklaşık 88,4 sn'de tamamlandı. HTTP 200 ile indirilen PNG'nin SHA-256'sı outcome ve kontrollü deney çıktısıyla aynı: `34317c7d05eebfc811f5ae634715734f4c1c603743a2a501b7b35082a7669ad5`. Kayıt: `runs/upper-preservation-integration.json`; üretim: `runs/protected-outfit-c2ba086d`.
- Son Python kontrolü: 46 test, 45 geçti, CatVTON ortamına özel 1 test atlandı. .NET derlemesi 0 hata/uyarı. Yeni kontroller koruma sınırını, adımlar arası referans yörüngesini, alt bölgenin serbest kalmasını, kaynak ayrıştırıcı sözleşmesini ve hata sonrası temizliği sınar; görsel kalite puanı üretmez.

## Tekrar ve sınırlar

Proje sanal ortamı, yerel ağırlıklar, kaynak/maskeler ve proje içi çevrimdışı HF önbelleğiyle:

```powershell
.\.venv\Scripts\python.exe ai-worker/app/upper_preservation_probe.py runs/protected-outfit-d78dd586 runs/protected-outfit-fb56c42d
```

Yeni araç ayrıca yalnız üst kıyafet iç bölgesinin farkını kaydeder. Yukarıdaki ilk iki koşu bu ek ölçüm alanları eklenmeden çalıştırıldı; tablodaki sayılar kayıtlı birleşik koruma bölgesine aittir.

Bu iki örnek on ürünlük 7/10 oranını değiştirmez. Kaynak eteğin kemeri, pantolon paçası, ilk aşamada zaten oluşmuş ürün hataları ve ayrıştırıcı sınır hataları çözülmedi. Sonraki adım, bel/paça doğruluğunu üst koruma açıkken ayrı kontrollü deneyde incelemek ve diğer profil/kombinlerde gerileme değerlendirmesi yapmaktır.

## Bu çalışmada değişen dosyalar

- `ai-worker/app/upper_preservation.py`: yeni üretim kısıtı.
- `ai-worker/app/outfit.py`: mevcut bellek uyarlamalı pipeline'a isteğe bağlı koruma bağlantısı.
- `ai-worker/app/masked_outfit.py`: yalnız alt aşama için koruma seçeneği.
- `ai-worker/app/local_job.py`: yerel işlerde korumayı açma ve yöntem kaydı.
- `ai-worker/app/upper_preservation_probe.py`: eski ilk aşamayı tekrar kullanan kontrollü karşılaştırma aracı.
- `ai-worker/tests/test_upper_preservation.py`: beş koruma davranış testi.
- `ai-worker/tests/test_masked_outfit.py`: yalnız alt aşamada etkinleştirme kontrolü.
- `docs/local-app.md`: güncel yerel üretim yöntemi.
- `docs/upper-preservation-results.md`: yöntem, kanıt, sınırlar ve dosya listesi.
- `docs/progress.md`: tamamlanan iş ve sonraki adım.

Yeni yerel görseller/iş kayıtları Git dışındaki `runs/` altında tutuldu; önceki çıktılar silinmedi.
