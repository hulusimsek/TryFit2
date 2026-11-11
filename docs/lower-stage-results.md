# Pantolon paçası ve etek kemeri takibi

11 Kasım 2026. Üst koruma sabit tutularak mevcut ürün kaynaklarıyla sekiz yeni alt aşama üretildi. Dolgun profilde kısa paça, hedefi maskelemeden fakat üst/ayak/alt zemin bağlamını üretim boyunca koruyarak azaltıldı. Yöntem yerel ekranın seçili `wide-trousers` ürünü için etkinleştirildi. Eteğin kemer/tokası çözülmedi; etekte önceki maskeli yöntem korundu.

Bu sonuçlar asistanın sınırlı görsel incelemesidir. On ürünlük kalite kapısı yeniden ölçülmedi; 7/10 oranı değişmez. Pantolon kaynağının ürün sayfasında AI üretim etiketi kayıtlıdır; bağımsız doğrulanmış gerçek fotoğraf olarak sayılmaz.

## Neden bu değişiklik?

Kaynak izolasyonları görsel olarak incelendi: etekte toka, pantolonda paça uçları maskenin içindedir. Sorunu maske dışındaki ayrıntı gibi ele alıp kaynakları değiştirmedik. FASHN alt gövdeyi maskelerken bacak bağlamını kaldırır. Aynı ilk aşamayı maskesiz alt üretime vermek paçayı uzattı, fakat dolgun profilde ayakları örttü. Yalnız ayak iç bölgesinin üretim kısıtı bu kez çevrede kumaş çıkıntıları bıraktı.

Son yöntem ayaklara ek olarak ayak başlangıç hizasından aşağıdaki zemin bağlamını da yumuşak geçişle referans yörüngesine bağlar. Referanstaki alt kıyafet veya çıplak bacak etiketleri bu zemin kısıtına alınmaz. Önceki üst koruma aynen sürer; bitmiş çıktıya piksel yapıştırılmaz. Bununla birlikte sonuç referans görüntüyle kısıtlanmıştır; modelin kendiliğinden koruması veya fiziksel oturuş simülasyonu değildir.

## Bütün denemeler

| Koşu | Değişiklik / adet | Gözlem ve karar |
| --- | --- | --- |
| `upper-preservation-35d6121d` | Üst koruma açık, yalnız alt hedef maskelemesi kapalı; bluz/etek ve tişört/pantolon, 2 üretim | Pantolon uzadı fakat ayaklar kapandı. Toka geri gelmedi. Varsayılan yapılmadı. |
| `upper-preservation-783b4a80` | Maskeli alt + üst koruma, yalnız guidance 1.5→2.5; aynı iki kombin, 2 üretim | Kemer veya paça için yeterli düzelme yok. Guidance 1.5 kaldı. |
| `upper-preservation-961b1a6d` | Önceki maskesiz dolgun profil üretimine yalnız ayak iç bölgesi kısıtı; 1 üretim | Ayaklar görünür; çevrede kumaş çıkıntıları. Kabul edilmedi. |
| `upper-preservation-2a831343` | Önceki kısıta alt zemin bağlamını ekleme; aynı dolgun profil, 1 üretim | Paça önceki maskeli yerel yönteme göre uzadı, ayaklar görünür ve belirgin çıkıntılar kayboldu. Sınırlı yerel yöntem seçildi. |
| `upper-preservation-ec87433b` | Aynı son yöntem, ince ve orta profilin mevcut ilk aşamaları; 2 üretim | Ayaklar görünür; önceki maskesiz çıktılara göre paça yığılması azaldı. Bu iki profilde "paça uzadı" iddiası yok. |

Tam dizinler `runs/` altındadır; her birinde `run.json`, SHA-256, süre ve karşılaştırma PNG/JPG'leri vardır. Dolgun profilde karşılaştırılan koşuların ilk aşama, seçim ve önceki sonuç hash'lerinin aynı olduğu ayrıca doğrulandı. Ayarlar seed 42, 30 adım, guidance 1.5'tir; yalnız ayrı guidance kontrolünde 2.5 kullanıldı. Önceki başarısız çıktılar korunur.

İlk maskesiz koşunun `controlled_change` açıklaması eski şablondan kalmıştır; gerçek `lower_stage_change` ve `settings.segmentation_free` alanları maskesiz çağrıyı kaydeder. İlk ayak/zemin koşusundaki açıklama da yalnız ayak içi kısıtı der; bu koşuda zemin desteği uygulanmıştır. Bu tarihsel kayıtlar değiştirilmedi. Bu açıklama ve `runs/trouser-followup-review/review.json` yöntem farkını belirtir; sonraki koşular açık yöntem adı ve uygulama kodu hash'lerini kaydeder.

[Dolgun profil: kaynak / önceki / başarısız denemeler / son yöntem](../runs/trouser-followup-review/comparison.jpg) · [Üç profil](../runs/trouser-followup-review/three-profiles.jpg).

## Tekrar

Proje sanal ortamı, ağırlıklar, eski girdiler ve proje içi çevrimdışı HF önbelleğiyle:

```powershell
.\.venv\Scripts\python.exe ai-worker/app/upper_preservation_probe.py runs/protected-outfit-fb56c42d --maskless-bottom --preserve-feet
.\.venv\Scripts\python.exe ai-worker/app/upper_preservation_probe.py runs/protected-outfit-8af482a6 runs/protected-outfit-a574f9b7 --maskless-bottom --preserve-feet
```

Deney aracı guidance ve maskeleme değişikliklerini aynı çağrıda reddeder. Ayak/zemin seçeneği yalnız açık maskesiz karşılaştırmada kullanılabilir. Kaynak ayrıştırma sözleşmesi ve durum temizliği korunur; ayak bulunamazsa sahte sonuç yerine hata verilir.

49 Python testi çalıştı: 48 geçti, ayrı CatVTON ortamı isteyen 1 test atlandı. .NET derlemesi 0 hata/uyarı. Bunlar görsel kalite puanı değildir.

Yerel API üzerinden dolgun profil + tişört + pantolon işi `a88904a9-045d-44bb-9402-989abc4d2566` yaklaşık 87,8 sn'de tamamlandı. HTTP 200 ile indirilen PNG'nin SHA-256'sı outcome ve son kontrollü sonuçla aynı: `99c74544eed3ea7f3a3683042c12168d9231b64a7d7876abec4e79515beb37b9`. `feetPreservation=true`, `bottomTargetMasked=false` alanları da doğrulandı. Kanıt: `runs/trouser-followup-review/integration.json`; gerçek üretim: `runs/protected-outfit-d77ed4d1`.

## Sınırlar ve sonraki adım

Paça birebir kaynak boyunda değildir. Ayak/zemin koruması kıyafetin ayakkabı üstüne yığılmasını veya ayakları örtmesini sınırlar; her uzun pantolon/poz için doğru varsayım sayılamaz. Bu nedenle yalnız seçili yerel pantolon için açık tutulur; diğer araştırma koşularında varsayılan kapalıdır. Kaynak bedeni, bel/cep/düğme doğruluğu ve kumaş fiziği garanti edilmez.

Etek tokası iki ayar denemesinde de geri gelmedi. Uzun üst kıyafet belin bir bölümünü örtebildiği için sonraki mantıklı adım, belin görünür olduğu kısa üstle aynı eteği ayrı kontrol etmek; örtülmeyi gerçek ayrıntı kaybından ayırmaktır. Yeni ürün fotoğrafı veya varsayılan model değiştirmeden önce bu kontrol yapılmalıdır.

## Bu turda değişen 8 dosya

- `ai-worker/app/upper_preservation.py`: maskesiz alt desteği ve isteğe bağlı ayak/zemin kısıtı.
- `ai-worker/app/masked_outfit.py`: ayak korumasını yalnız alt aşamaya aktarma.
- `ai-worker/app/upper_preservation_probe.py`: ayrı varyantlar, eski profil koşularıyla tekrar ve yöntem/kod hash kayıtları.
- `ai-worker/app/local_job.py`: seçili pantolon için yeni yöntem, etek için önceki yöntem ve açık outcome alanları.
- `ai-worker/tests/test_upper_preservation.py`: ayak/zemin sınırı, maskesiz kaynak sözleşmesi ve geçersiz deney ayarları kontrolleri.
- `docs/local-app.md`: güncel yöntem.
- `docs/lower-stage-results.md`: sonuçlar ve sınırlamalar.
- `docs/progress.md`: kısa tamamlanma kaydı ve sonraki adım.
