# Bilinen sorunlar ve eksikler

İnceleme tarihi: 11 Kasım 2026. Aşağıdaki bulgular kod ve mevcut deney kayıtlarından derlenmiştir; bu görevde yeni inference veya görsel puanlama yapılmadı. Öncelikler öneridir, onaylanmış iş takvimi değildir.

| ID | Öncelik / durum | Sorun ve etkisi | Kanıt / sonraki doğrulama |
| --- | --- | --- | --- |
| K01 | Yüksek / açık | Genel araştırma kalite kapısı geçilmedi. Model çıktı üretmesi ürün doğruluğu anlamına gelmiyor. | Ham koşu 4/10, SAM kaynak maskeli koşu 7/10, tüm hedefleri maskeleyen ayrı koşu 5/10. [Protokol](evaluation-protocol.md) eşiği 8/10. Oranlar asistanın görsel ön değerlendirmesi; bağımsız panel değil. |
| K02 | Yüksek / açık | Oversize hacim, ürün/kol boyu ve açık fermuarlı katman korunması yetersiz olabiliyor. | [Kaynak izolasyonu](source-isolation-results.md), [kesim deneyleri](cut-probes-results.md). TODO: zor örnekleri koruyarak yeni kontrollü koşu. |
| K03 | Yüksek / kısmen iyileşti | İkinci parça üretimi ilk parçanın etek ucunu, beli veya ayakları değiştirebiliyor. | [Üç profil](avatar-suite-results.md), [ayak kontrolü](feet-input-results.md). Maskeli alt aşamada üç örnekte ayaklar görünür kaldı; paça kısalması ve üst değişimi sürüyor. Yerel bluz/etek sonucunda kemer/toka korunmadı. |
| K04 | Yüksek / kapsam eksikliği | Otomatik ürün görseli seçme/ayırma yok. SAM maskeleri araştırmacı destekli; seçilmiş girdilerle alınan sonuçlar rastgele ürün URL'lerine genellenemez. | `evaluation/annotations`, [kaynak izolasyonu](source-isolation-results.md). TODO: otomasyon ancak ayrı gerçek girdilerle değerlendirilsin. |
| K05 | Yüksek / doğrulanmadı | Gerçek beden uyumu, kumaş fiziği ve boy/kilodan vücut üretimi yok. | [Yerel ekran](local-app.md), `avatar-profiles.json`. Üç hazır sentetik profil ölçülü rekonstrüksiyon değildir. |
| K06 | Yayın engeli / açık | Çok kullanıcılı kimlik doğrulama ve iş/sonuç sahipliği denetimi yok. Sonuç erişimi iş kimliğine dayanıyor. | `TryOnEndpoints.cs`, `TryFitJob.cs`. Loopback dinleme yerel kapsamı sınırlar; kullanıcı izolasyonu sağlamaz. TODO: dış erişimden önce sahiplik ve başka kullanıcının görüntüsüne erişememe kontrolü. |
| K07 | Yayın engeli / açık | Uzak GPU adaptörü ve bağımsız worker dağıtımı uygulanmadı. | `PythonTryOnEngine.cs`, `LocalWorkspace.cs`: aynı makinenin `.venv`, dosya sistemi ve model ortamı kullanılıyor. TODO: yerel GPU'suz backend ile uzak gerçek inference doğrulaması. |
| K08 | Yayın engeli / doğrulama gerekli | Araştırma lisansı kısıtları ticari dağıtımı etkiliyor. | README ve [CatVTON notları](catvton-results.md), FASHN insan ayrıştırıcısı için araştırma/değerlendirme kısıtı bildiriyor. TODO: tam bağımlılık zincirinin güncel lisanslarını yayın öncesi doğrula; ana model lisansı tek başına yeterli değil. |
| K09 | Orta / bilinen sınır | Kuyruk bellekte; yeniden başlatmada aktif işler devam etmiyor, başarısız oluyor. | `InMemoryJobQueue.cs`, `TryOnJobs.RecoverInterruptedJobs`. Tek süreç araştırması için mevcut tercih; kalıcı kuyruk/retry veya çok sunucu garantisi yok. |
| K10 | Orta / açık | `/api/health` modelin çalışabildiğini doğrulamıyor. | `PythonTryOnEngine.IsReady` sadece Python yürütülebilir dosyasının varlığını kontrol ediyor. TODO: uzak worker tasarımında gerçek hazırlık kontrolü; bugünkü `ready` inference kanıtı sayılmasın. |
| K11 | Orta / eksik doğrulama | .NET test projesi mevcut çözümde yok; mobil ve uzak üretim akışı doğrulanmadı. | `TryFit.sln`, [yerel doğrulama](local-app.md). Python davranış testleri görsel kaliteyi ölçmez. TODO: değişen iş kuralları ve gizlilik sınırları için anlamlı testler. |
| K12 | Orta / ortam bağımlılığı | Git dışındaki ağırlıklar, girdiler, maskeler ve ortam olmadan temiz kopya aynı ekranı çalıştırmayabilir. CatVTON ortamı ana ortamın paket yoluna bağlı. | `.gitignore`, [CatVTON kurulumu](catvton-results.md). TODO: minimum tekrar üretim kurulumu ve bağımsız worker paketi. |
| K13 | Orta / veri belirsizliği | Ürün kaydı gerçek olsa da her kaynak görselin fotoğraf kökeni doğrulanmış değil; geniş pantolon kaynağında AI üretim etiketi kayıtlı. | [İlk on ürün raporu](benchmark-10-results.md). “On gerçek ürün” ifadesi “on bağımsız doğrulanmış gerçek fotoğraf” diye yorumlanmamalı. |
| K14 | Orta / açık (çözülmedi) | `slender + tshirt + tuckTop=false` koşusunda etek rengi koyu kömürden sıcak kahverengiye kayıyor. Maske bel/etek satırlarında bazla aynı olmasına karşın ayak bileği alt sınır genişlemesi CatVTON UNet ham üretimini (`02-skirt-raw.png`) etkiliyor. | `ba156bf7` (`RGB 71.1, 54.2, 44.1`) vs baz `25a9b1d3` (`RGB 47.5, 41.7, 40.0`); `cat-soft-mask.png` `0..859` satırları `0` fark, yalnızca `860..916` bilek bandı farklı. Gelecekte ele alınacak. |
| K15 | Orta / açık (çözülmedi) | `fuller + patterned-blouse + tuckTop=true` koşusunda bel beyaz şeridi giderilmesine karşın kemer C-tokasının parlaklık/kontrastı zayıflıyor (`02-skirt-raw.png` kaynaklı) ve kemerin sağ üst kenarı hafif yükseliyor. | `f1fa3bfd` (`max=175.4`, `p99=51.8`, luma `>100` `18` px) vs baz `6304adf4` (`max=252.0`, `p99=197.7`, luma `>100` `111` px). Gelecekte ele alınacak. |

## Tamamlanmamış ürün kapsamı

Yeni projede ayrı tüketici frontend'i, Chrome eklentisi, yeni Trendyol URL'sinden ürün alma ve kişisel fotoğraf yükleme tamamlanmış değildir. Mevcut ekran üç profil ve dört ürüne sınırlıdır; bu eksikler çalışan özellik diye sunulmaz.

## Kayıt ve takip

Yeni soruna yeniden üretim adımları, etkilenen dosya/koşu, beklenen-gerçek davranış ve kapanış kanıtı eklenmelidir. Geçici iyileşme tam çözüm sayılmaz; başarısız çıktılar korunur. Ücretli kaynak veya ek bağımlılık gerektiren çözüm otomatik uygulanmaz.
