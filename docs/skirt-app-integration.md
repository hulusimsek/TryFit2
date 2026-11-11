# Yerel ekranda etek kemeri düzeltmesi

11 Kasım 2026. **Etek üretimi artık yerel ekranda gerçek FASHN üst → CatVTON etek akışına bağlı.** Orta profil tişört/etek, orta profil bluz/etek ve dolgun profil tişört/etek işlerinde toka görünür üretildi. Önceki araştırma görselleri sonuç yerine kullanılmadı.

## Ekrandaki kullanım

Pileli mini etek seçildiğinde **Üstü eteğin içine al** varsayılan açıktır. Bu, üstün alt kısmını içeri alınmış biçimde yeniden üretmeye izin verir; orijinal etek ucunun aynen korunması değildir. Seçenek kapatılırsa uzun üst kemeri örtebilir. Pantolonda bu seçenek gönderilmez; API de pantolon + `tuckTop=true` isteğini 400 ile reddeder.

[Doğrulanan yeni tişört/etek sonucunu ekranda aç](http://127.0.0.1:5187/?job=46fbbd4b-c8b2-4b00-a10a-90f55eebd8db). [Gerçek ekran görüntüsü](../runs/skirt-app-integration/screen.jpg).

Eski tarayıcı önizlemeleri yeni motor sonucu olarak geri getirilmez. Yeni işin kimliği URL ve tarayıcı kaydına yazılır; yenilemede aynı sonuç ve giyim seçimi yüklenir. Statik yanıtlar `no-store`, JS/CSS bağlantıları sürümlüdür; eski HTML/yeni JS karışımından kaçınılır. Eski iş dosyaları silinmedi.

## Gerçek worker akışı

1. API seçimi doğrular; `TuckTop` Domain seçimi ve saklama DTO'sunda taşınır. Eski kayıtlarda false varsayılır. HTTP katmanına model veya iş kuralı eklenmedi.
2. `local_job.py`, etekte `local_skirt.py` yolunu çalıştırır. İlk ayrı `.venv` süreci yeni gerçek FASHN üst üretir ve gerçek insan ayrıştırmasını yapar.
3. O görüntüden etek düzenleme alanı, üst/el/ayak/ten koruması ve yumuşak arka plan geçişi hazırlanır. İçeri alma seçeneği üstün tespit edilen yüksekliğinin yaklaşık alt %22'sinin yeniden üretilmesine izin verir. Kesim/örtülme yaklaşık kalabilir.
4. Üst süreci kapanır; GPU belleği boşalır. Ayrı `.venv-catvton` süreci, hash'li `skirt-handoff.json` dosyalarını doğrular. Mevcut CatVTON ağırlıkları da kayıtlı hash'lere karşı kontrol edilir. Yeni etek gerçek inference ile üretilir.
5. Ham `02-skirt-raw.png` ve `02-skirt-repaint.png` ayrı saklanır. Repaint, düzenleme alfası sıfır olan hedef piksellerini kopyalar. Ekrana bu repaint sonucu gider; bu koruma modelin öğrendiği kimlik yeteneği olarak sunulmaz. Pantolon yolu önceki FASHN akışıdır.
6. Süreç hatası, eksik ortam veya değiştirilmiş ara dosya başarıya çevrilmez; hazır görsel fallback'i yoktur. Alt süreçler aynı süreç ağacında kalır; mevcut .NET süre sınırı/iptal tüm ağacı sonlandırabilir. İlerleme mesajları Windows'ta açık stdout/stderr yönlendirmesiyle taşınır.

## Gerçek API/ekran doğrulaması

| İş | Seçim | Süre / sonuç |
| --- | --- | --- |
| `46fbbd4b-c8b2-4b00-a10a-90f55eebd8db` | Orta, tişört + etek, içeri al | Yaklaşık 95,9 sn; toka görünür. Tarayıcıda seçim, tamamlanma ve indirme bağlantısı görüldü. |
| `e683d39a-ea71-44be-9808-1710fa476650` | Orta, bluz + etek, içeri al | Yaklaşık 90,1 sn; toka görünür. |
| `292dad28-c31d-489a-95ea-f45f72a077f3` | Dolgun, tişört + etek, içeri al | Yaklaşık 90,5 sn; toka görünür. Kuyruk beklemesi bu üretim süresine dahil değil. |

Üç indirme HTTP 200; PNG SHA-256 değerleri outcome ile eşleşti. [İş/indirme kayıtları](../runs/skirt-app-integration/jobs.json). Sunucu işler bittikten sonra yeniden başlatıldı: üç tamamlanmış iş ve `tuckTop=true` geri yüklendi; eski iş kaydı false ile açıldı. Geçersiz stil ve bool türü 400 ile reddedildi. [Kontrol kaydı](../runs/skirt-app-integration/checks.json).

İlk iki entegrasyon üretimi (`4de8a48b-…`, `b5b3dc8a-…`) kemeri gösterse de arka plan şeritleri nedeniyle kabul edilmedi. Düzenleme zarfı vücut çevresine daraltıldı, zemin geçişi yumuşatıldı ve gereksiz alt bacak alanı maskeden çıkarıldı. Bu olumsuz çıktılar korunmuştur. Eski önizleme tanı görüntüleri ilk zarfı gösterebilir; inference'ta kullanılan gerçek sert/yumuşak maskeler her iş dizininde ayrıdır.

Ana ortam: 65 test, 64 geçti, CatVTON'a özel 1 atlandı. Ayrı CatVTON ortamında ilgili 9 test geçti. Son .NET derlemesi 0 hata/uyarı. Yeni kontroller giyim seçiminin maskeye etkisini, korunacak el/ayak alanlarını, değiştirilmiş ara dosyanın reddini ve alt süreç başarısızlığında sonuç oluşturulmamasını sınar.

## Sınırlar ve sonraki adım

Bu düzeltme yalnız seçili araştırma ürünleri ve hazır profillerle doğrulandı. Bazı çıktılarda ayak bileği geçiş izi veya kıyafet kenarı izi kalabiliyor; kaynak kesimi, gerçek ürün bedeni, kumaş fiziği ve genel kalite kapısı çözülmüş değildir. CatVTON/human-parser araştırma lisansı sınırları sürer; ticari veya çok kullanıcılı yayın yapılmadı.

Sonraki mantıklı adım: çalışma anındaki maske hazırlığını kalan profil/üst seçimlerinde kontrol etmek ve ayak bileği/kenar geçiş izlerini ayrı bir kontrollü düzeltmeyle azaltmak. Çalışan kemer akışı bu sırada korunmalıdır.

## Değişen 17 dosya

- `src/TryFit.Domain/TryFitJob.cs`.
- `src/TryFit.Application/TryOnJobs.cs`.
- `src/TryFit.Infrastructure/FileJobRepository.cs`.
- `web/TryFit.Local/TryOnEndpoints.cs`.
- `web/TryFit.Local/Program.cs`.
- `web/TryFit.Local/wwwroot/index.html`.
- `web/TryFit.Local/wwwroot/app.js`.
- `web/TryFit.Local/wwwroot/style.css`.
- `ai-worker/app/local_job.py`.
- `ai-worker/app/local_skirt.py`.
- `ai-worker/app/local_skirt_inputs.py`.
- `ai-worker/tests/test_local_skirt.py`.
- `README.md`.
- `docs/local-app.md`.
- `docs/architecture.md`.
- `docs/skirt-app-integration.md`.
- `docs/progress.md`.
