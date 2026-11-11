# Görev şablonu

Bu şablonu yeni görev açıklamasına kopyalayın. İlgisiz bölümleri kaldırın; bilinmeyenleri TODO olarak bırakın. [AGENTS.md](../AGENTS.md) bağlayıcıdır. Büyük görevde kısa uygulama planı sunulup onay beklenir; küçük ve açık görev doğrudan yapılabilir.

## Görev

- Başlık / tarih: TODO
- Problem ve kullanıcıya etkisi: TODO
- İstenen somut sonuç: TODO
- Mevcut davranış ve kanıt (dosya, hata, run kimliği): TODO

## Kapsam ve sınırlar

- Değiştirilecek ilgili dosyalar/bileşenler: TODO
- Kapsam dışı işler: TODO
- Domain/Application/Infrastructure/API sorumlulukları ve etkilenen sözleşme: TODO veya uygulanmaz
- Yeni bağımlılık gerekiyorsa somut gerekçe: TODO veya yok
- Maliyet: TODO. Ücretli kaynak/servis açık onay olmadan sağlanmaz.
- Eski `TryFit` deposu yalnızca referanstır; hiçbir dosyası değiştirilmez. Kullanıcı çalışması izinsiz silinmez veya üzerine yazılmaz.

## Ön inceleme

- İlgili mevcut dosyalar ve proje kuralları: TODO
- Doğrulanmış bilgiler: TODO
- Bilinmeyenler / varsayımlar: TODO
- Referanstan çıkarılan ders ve kaynağı: TODO veya uygulanmaz

## Kısa plan

1. TODO
2. TODO
3. TODO

Görev büyükse plan onayı: TODO. Onay gerekliliği AGENTS.md'den gelir. Mevcut görev kapsamı dışındaki değişiklikler ayrıca değerlendirilir.

## Kabul ölçütleri

- [ ] Beklenen davranış, somut girdi/çıktıyla doğrulandı: TODO
- [ ] Hata/sınır durumu ve beklenen yanıt tanımlandı: TODO
- [ ] Bağımlılıklar iç katmanlara yöneliyor; iş mantığı HTTP veya altyapı katmanına taşınmadı.
- [ ] İlgili test/derleme veya belge kontrolleri tamamlandı; çalıştırılamayan kontrolün nedeni yazıldı.
- [ ] Kullanıcı görselleri/sonuçları başka kullanıcıya açılmıyor; ilgiliyse sahiplik kontrolü doğrulandı.
- [ ] Çalışmayan özellik ve hazır örnek, çalışan üretim gibi sunulmadı.

## AI deneyi ise

- Gerçek ürün/görsel kaynağı, kullanım izni ve köken belirsizlikleri: TODO
- Hedef görüntü/profil ve ölçülü olup olmadığı: TODO
- Model/kod revision'ı, ağırlık hash'leri, ortam sürümleri: TODO
- Kategori, seed, adım, guidance, kaynak/hedef maskesi ve araştırmacı müdahalesi: TODO
- Kontrol koşusu, tek değişken ve yeni run dizini: TODO
- Ham çıktı / kompozit ayrımı, hash, süre, bellek, hata kayıtları: TODO
- [Değerlendirme protokolü](evaluation-protocol.md), değerlendirici ve kalite sonucu: TODO
- Başarısız/üretilmeyen örnekler korunur; `completed` kalite başarısı sayılmaz. Ayrı koşuların iyi sonuçları birleştirilmez.
- Gerçek beden uyumu, genelleme veya ticari lisans uygunluğu ayrıca doğrulanmadıysa iddia edilmez.
- Üretim hedefi uzak GPU'dur; yerel deney backend'e kalıcı yerel GPU zorunluluğu getirmez. 3D manken akışı eklenmez.

## Doğrulama kaydı

| Kontrol / komut | Sonuç | Kanıt veya çalıştırılamama nedeni |
| --- | --- | --- |
| TODO | TODO | TODO |

Yalnızca gerçekten yürütülen kontroller yeni sonuç olarak raporlanır. Geçmiş test kayıtları tarih/kaynakla ayrı belirtilir. Doküman değişikliğinde ilgili bağlantı, içerik tutarlılığı ve değişen dosya kapsamı kontrol edilir; gereksiz GPU çalıştırılmaz.

## Teslim

- Tamamlanan işler ve değişen dosyaların tam listesi: TODO
- Doğrulama sonuçları ve sınırlamalar: TODO
- Açık sorunlar / TODO'lar: TODO
- Önerilen sonraki adımlar (tamamlanan işlerden ayrı): TODO
- Gerekiyorsa güncellenecek belgeler: [mimari](architecture.md), [kararlar](decisions.md), [bilinen sorunlar](known-issues.md), [ilerleme](progress.md).
