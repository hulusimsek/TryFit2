# İlerleme

Durum tarihi: 11 Kasım 2026. Bu dosya kod ve diskteki kayıtların incelemesine dayanır; önceki görevlerin tamamlanma tarihleri tahmin edilmez. Aşağıdaki test/üretim sonuçları mevcut kayıtlardır, bu dokümantasyon görevinde yeniden çalıştırılmış sonuçlar değildir.

## Mevcut ve kayıtla desteklenen işler

| Alan | Mevcut durum | Kanıt |
| --- | --- | --- |
| .NET iskeleti | Domain, Application, Infrastructure ve Local projeleri `net9.0` hedefliyor; bağımlılıklar içe yöneliyor. | [Çözüm](../TryFit.sln), [mimari](architecture.md). |
| Yerel araştırma ekranı | Üç hazır profil, dört ürün, üst+alt seçimi, iş takibi ve PNG sonucu için kod mevcut. | [Yerel ekran](local-app.md), `web/TryFit.Local`, `ai-worker/app/local_job.py`. |
| İş yönetimi | Seçim doğrulama, üç aktif iş sınırı, sıralı yürütme, JSON kayıt ve kesinti kurtarma davranışı mevcut. | `TryOnJobs.cs`, `RunTryOnJob.cs`, `TryOnWorker.cs`, `FileJobRepository.cs`. Kurtarma aktif işi devam ettirmez; başarısız yapar. |
| Gerçek yerel üretim kayıtları | İki kombin işi `completed`; HTTP ve indirme hash kontrolleri kayıtlı. | `runs/local-app-validation.json`: dolgun profil tişört+pantolon yaklaşık 87 sn, orta profil bluz+etek yaklaşık 79 sn. Bu süreler performans garantisi değil. |
| Araştırma araçları | Colab notebook, manifestler, değerlendirme, hash/süre/bellek kayıtları ve çevrimdışı rapor araçları var. | `notebooks`, `evaluation`, `ai-worker/app/experiment.py`, `scripts`. Ücretsiz Colab oturumunun bugün GPU sağlayacağı doğrulanmadı. |
| Önceki teknik kontroller | Yerel doğrulama kaydı 40 Python testi, 1 atlama, 0 başarısızlık; .NET derlemesi 0 hata/uyarı bildiriyor. | `runs/local-app-validation.json`, [açıklama](local-app.md). Bunlar AI kalite testleri değil; bu görevde tekrar edilmedi. |

## Deney sonuçları

Bu tablo görsellerin bu görevde yeniden değerlendirilmesi değildir. Sayılar kayıtlı asistan görsel ön değerlendirmeleridir; bağımsız kullanıcı paneli veya genel kullanıcı başarı oranı değildir.

| Deney | Kayıtlı sonuç | Yorum / kaynak |
| --- | --- | --- |
| İlk hoodie + pijama kombini | Kıyafet kimliği testini geçmedi. | [İlk bulgular](first-outfit-results.md). Kaynak galeri fotoğrafı ve koruma maskesiyle tek örnek iyileşti: [takip](outfit-followup.md). |
| İlk on ürün | 4/10 | `runs/20261110T003636Z-688ebfd6`; [rapor](benchmark-10-results.md). |
| SAM kaynak maskeli on ürün | 7/10, kalite kapısı `failed` | `runs/20261110T095148Z-cf9135a6/quality.json`; [rapor](source-isolation-results.md). Maskeler araştırmacı destekli. |
| Kesim için ek kontroller | Genel sonuç 7/10 kaldı. | [Dokuz ek çıktı](cut-probes-results.md); ilk koşunun puanı yeniden yazılmadı. |
| CatVTON karşılaştırması | Üç zor mankenli kaynakta 0/3 | [Yöntem ve ayrı düz ürün kontrolleri](catvton-results.md). FASHN 7/10 oranına eklenmedi; varsayılan yapılmadı. |
| Kaynak maskeli iki parça / üç profil | Kombin çıktıları kayıtlı; genel kapı geçilmiş değil. | [Kombin](masked-outfit-results.md), [üç profil](avatar-suite-results.md). |
| Yalnız alt aşamada hedef maskesi | Üç profilde ayaklar görünür; paça/üst değişimi sürüyor. | [Kontrollü takip](feet-input-results.md). Fiziksel oturuş doğrulanmadı. |
| On ürünün tamamında hedef maskesi | 5/10, kalite kapısı `failed` | `runs/20261110T134441Z-be46a99c/quality.json`; [rapor](target-mask-benchmark-results.md). Yerel ekranın karma iki aşamalı yöntemiyle aynı deney değil. |

Araştırma eşiği on örnekte en az sekiz kabul edilebilir sonuçtur. Mevcut 7/10 ve 5/10 koşuları bu eşiği karşılamaz. Farklı koşulardan başarılı ürünler seçilerek birleşik bir başarı oranı üretilmedi.

## Henüz tamamlanmayanlar

- Bağımsız değerlendirmeyle kalite kapısı ve farklı kişi/pozlarda genelleme; iki parçalı karma yöntem için ayrı geniş test.
- Üretimde uzak GPU, bağımsız worker dağıtımı ve yerel GPU'suz backend doğrulaması.
- Ayrı tüketici frontend'i ve Chrome eklentisi; otomatik Trendyol ürün/görsel alma.
- Kullanıcı fotoğrafı yükleme, kimlik doğrulama, kullanıcıya özel iş/görsel erişimi ve silme politikası.
- Boy/kilodan ölçülü vücut üretimi, gerçek ürün bedeni uyumu ve kumaş fiziği doğrulaması.
- Ticari dağıtım için tüm model/yardımcı bileşen lisanslarının uygunluk doğrulaması.

## Önerilen sonraki adımlar — uygulama yapılmadı

1. [Bilinen sorunlardaki](known-issues.md) kıyafet kimliği ve katman koruma hataları için tek değişkenli deney tanımla; eski başarısız çıktıları koru.
2. Aynı rubrikle bağımsız değerlendirici ve farklı hedef görüntüler kullan; genelleme ve kombin sonuçlarını ayrı raporla.
3. Kalite, gizlilik, lisans ve bütçe koşulları netleşince en küçük uzak worker sözleşmesini uygula. Ücretli kaynağa açık onay olmadan geçme.

## Bu dokümantasyon çalışması

11 Kasım 2026: `AGENTS.md`, ilgili kod, mevcut deney belgeleri/kayıtları ve eski TryFit'in seçili kaynakları incelendi. Önceden boş olan `architecture.md`, `decisions.md`, `known-issues.md`, `progress.md`, `task-template.md` dolduruldu. Kod veya AGENTS.md değişikliği, model çalıştırma, servis sağlama ve dağıtım bu görevin kapsamında değildir.

## Devam öncesi kontrol — 11 Kasım 2026

- `AGENTS.md`, ilerleme ve ilgili yerel uygulama/kalite belgeleri ile iş akışı kodu incelendi. Eski TryFit deposuna dokunulmadı.
- `dotnet build TryFit.sln --no-restore`: 0 hata, 0 uyarı. Proje sanal ortamıyla Python testleri yeniden çalıştırıldı: 40 testin 39'u geçti, ayrı CatVTON ortamı gerektiren 1 test atlandı.
- Kontrol anında 5187 portunda dinleyen yerel uygulama yoktu. Yeni inference veya görsel kalite değerlendirmesi yapılmadı; kayıtlı kalite oranları değişmedi.

Sonraki mantıklı adım: kapsamlı çalışma planı onaylandıktan sonra yerel ekranı başlatıp gerçek bir kombin üretimini doğrulamak; görülen kıyafet kimliği/ikinci parça koruma hatasını mevcut yöntemle karşılaştırılan sınırlı bir deneyle ele almak. Kalite sorunu henüz çözülmedi.

## Üst kıyafeti koruma — 11 Kasım 2026

- Yerel ekran başlatıldı; mevcut bluz/etek üretimi yeniden doğrulandı. Alt aşamada üst/kimlik iç bölgelerini her üretim adımında koruyan kısıt uygulandı ve yerel worker'a bağlandı. Bitmiş sonuca piksel yapıştırılmadı.
- Aynı ilk aşamalarla iki kontrollü karşılaştırma tamamlandı: bluz/etek ve dolgun profil tişört/pantolon. Korunan bölgenin ortalama kanal farkı sırasıyla 7,49→0,13 ve 1,33→0,79 oldu; bu bir kalite başarı oranı değildir. Bluz deseni/ucu daha iyi korundu; kemer/toka ve kısa paça hataları sürüyor. Eski çıktılar korundu.
- Güncel API işi yaklaşık 88,4 sn'de tamamlandı; indirilen PNG'nin SHA-256'sı kontrollü sonuçla eşleşti. Python: 46 testin 45'i geçti, ayrı CatVTON ortamı isteyen 1 test atlandı. .NET: 0 hata/uyarı.
- [Yöntem, kanıtlar ve değişen 10 dosya](upper-preservation-results.md). Genel 7/10 kalite oranı değişmedi.

Sonraki mantıklı adım: üst korumayı sabit tutarak bel/kemer ve paça hatasına odaklanan kontrollü düzeltme; ardından kalan profil/kombinlerde görsel gerileme kontrolü.

## Pantolon paçası takibi — 11 Kasım 2026

- Sekiz gerçek alt aşama üretimiyle maskeleme, guidance ve ayak koruma varyantları karşılaştırıldı. Kaynak maskelerinde toka/paça uçları bulunduğu doğrulandı; kaynaklar ve eski çıktılar korunuyor.
- Seçili pantolonda hedef maskesiz, üst + ayak/alt zemin korumalı yöntem uygulandı. Dolgun profilde kısa paça azaldı; üç hazır profilde ayaklar görünür, belirgin kumaş çıkıntıları görülmedi. İnce/orta profilde paça yığılması azaldı; birebir kaynak boyu/beden doğruluğu kanıtlanmadı. Etek tokası çözülmedi, etek yöntemi değiştirilmedi.
- Yeni yerel API işi 87,8 sn'de tamamlandı; indirilen PNG'nin SHA-256'sı kontrollü sonuçla aynı. Python: 49 test, 48 geçti, CatVTON ortamına özel 1 atlandı. .NET: 0 hata/uyarı. Genel 7/10 kalite oranı değişmedi.
- [Koşular, karşılaştırma görselleri, sınırlar ve değişen 8 dosya](lower-stage-results.md).

Sonraki mantıklı adım: belin açıkça görünür olduğu kısa üstle aynı eteği kontrol ederek tokadaki gerçek ayrıntı kaybını üst kıyafetin örtmesinden ayırmak.

## Açık gövde koruması — 11 Kasım 2026

- Sentetik kısa üst kontrolü ve aynı gerçek etekle altı üretim tamamlandı. Toka kısa üstte ve iki kaynak kadrajında da aktarılmadı; yalnız örtülme sorunu olmadığı görüldü. Başarısız yöntemler varsayılan yapılmadı.
- Eksik `torso` koruması eklendi; alt parça eklenirken açık karın iç bölgesinin kapanması düzeltildi. Aynı hedefte referansa ortalama kanal farkı 36,40→0,07; bu bir ürün kalite puanı değildir.
- Bluz/etek API üretimi ve PNG indirme/hash kontrolü tamamlandı. Python: 52 test, 51 geçti, CatVTON'a özel 1 atlandı. .NET: 0 hata/uyarı. Toka sorunu ve genel kalite kapısı açık.
- [Kanıtlar, sentetik hedef/prompt kaydı ve değişen dosyalar](waist-control-results.md).

Sonraki mantıklı adım: aynı eteğin alternatif gerçek kaynak fotoğrafıyla kemer/toka aktarımını, gövde koruması açıkken karşılaştırmak.

## Etek kaynak karşılaştırması — 11 Kasım 2026

- Aynı ürün galerisinden iki alternatif ön fotoğraf seçildi, SAM maskeleri çıkarılıp toka/el ayrımı kontrol edildi. Eski kaynakla birlikte aynı hedef/ayarlarla üç gerçek üretim tamamlandı; başlangıç sonucu öncekiyle SHA-256 düzeyinde aynı.
- İki alternatif de tokayı aktarmadı. Toka sorunu açık; katalog ve 7/10 kalite oranı değiştirilmedi. Başarısız çıktılar korundu.
- Kaynak karşılaştırma aracı ve doğrulama kontrolleri eklendi. Python: 56 test, 55 geçti, CatVTON'a özel 1 atlandı; son kaynak doğrulama değişikliğinin ilgili 4 testi de geçti. .NET: 0 hata/uyarı. [Kanıtlar ve değişen 7 dosya](skirt-gallery-results.md).

Sonraki mantıklı adım: aynı etek ve kısa üst hedefiyle mevcut ikinci modeli sınırlı karşılaştırmak; kaynak fotoğrafı aramasını şimdilik büyütmemek.

## CatVTON etek karşılaştırması — 11 Kasım 2026

- Aynı üç kaynak ve kısa üst hedefiyle üç CatVTON üretimi tamamlandı. İlk iki kaynakta gümüş toka görünür; üçüncüde biçim/rengi yanlış. Ayrı tek örneklik bel maskesi takibinde gri tayt şeridi giderildi, toka görünür kaldı.
- Dört ham ve dört repaint çıktı/hash kaydı doğrulandı. Repaint'in maske dışını hedeften kopyaladığı ayrı ölçüldü; genel kalite veya beden doğruluğu kanıtlanmadı. Yerel FASHN motoru ve önceki oranlar değiştirilmedi.
- Ana ortam: 59 test, 58 geçti, 1 atlandı; CatVTON ortamında ilgili 7 test geçti. .NET: 0 hata/uyarı. [Kanıtlar, sınırlar ve değişen 8 dosya](catvton-skirt-results.md).

Sonraki mantıklı adım: aynı eteği diğer iki hazır hedefte ve gerçek üst+alt kombininde kontrol etmek; maske/ham/repaint genellemesini görmeden yeni motoru yerel uygulamaya bağlamamak.

## CatVTON profil ve kombin kontrolü — 11 Kasım 2026

- İnce/dolgun hazır hedefler ve gerçek FASHN bluz aşamasıyla altı üretim tamamlandı. İlk maske sınırları el/üst piksellerini etkiliyordu; hedef/hash bağı doğrulanan koruma maskesiyle sert/yumuşak alfa bu bölgelerde sıfırlandı.
- Takipte seçilen üst/el/ayak bölgeleri üç hedefte repaint ile birebir korundu. Bluz/etek kombinindeki gri bel şeridi giderildi, toka görünür kaldı; dolgun hedefte pile görünümü iyileşti. Uzun üstte gizlenen kemer başarı sayılmadı; beden/genel kalite kanıtlanmadı.
- On iki ham/repaint PNG hash'i doğrulandı. Ana ortam: 61 test, 60 geçti, 1 atlandı; CatVTON'da ilgili 9 test geçti. .NET: 0 hata/uyarı. [Kanıtlar ve değişen 13 dosya](catvton-profile-results.md).

Sonraki mantıklı adım: sınırlı etek akışını yerel araştırma ekranına ayrı, açıkça deneysel model seçeneği olarak bağlamak; çalışma anında maske hazırlığı ve ham/repaint kaydını korumak.

## Etek kemeri ekran entegrasyonu — 11 Kasım 2026

- Ekrandaki etek işi yeni FASHN üst + ayrı CatVTON etek üretimine bağlandı. Varsayılan açık “Üstü eteğin içine al” seçimi API/iş kaydına taşındı; maske her yeni üstten hazırlanıyor, eski araştırma sonucu kullanılmıyor.
- Orta tişört/etek, orta bluz/etek ve dolgun tişört/etek API işlerinde toka görünür üretildi. İlk iki lekeli deneme korundu; arka plan maskesi düzeltildi. Üç indirme/hash kontrolü, gerçek ekran görünümü ve yeniden başlatma sonrası seçim/sonuç geri yükleme doğrulandı.
- Ana ortam: 65 test, 64 geçti, 1 atlandı; CatVTON'da ilgili 9 test geçti. .NET: 0 hata/uyarı. [Kanıtlar, kalan görsel sınırlar ve değişen 17 dosya](skirt-app-integration.md). Genel kalite/beden doğruluğu iddiası yok.

## Etek maskesi doğrulama ve ayak bileği geçişi — 12 Kasım 2026

- 12 kombinasyonluk baz matris tamamlandı (`a216d478`, `d9b2a047`, `6304adf4`, `25a9b1d3`, `8f51a18b`, `9e8f0102` eklendi ve görsel olarak incelendi). Tüm baz koşularda ayak bileğinde yatay tayt paçası izi; `slender` (`d9b2a047`) ve `fuller` (`6304adf4`) `patterned-blouse + tuckTop=true` koşularında ise bel `cut` çizgisinde beyaz yatay şerit hatası görüldü.
- Deney 1 (`8d91ec6b` orta, `ff674894` ince, `50d5167e` dolgun; çıktılar `runs/local-jobs/` altında korundu): `end` + `feet_fade` ile eklenen `calf_outward` değişikliği ayak bileği izini kaldırıp tokayı korusa da baldırlarda belirgin ~5px parlak halo ve `slender` sol etek ucunda çapraz çentik regresyonu oluşturdu; kabul edilmedi.
- Deney 2 (`a4503a54ef6f4e079d7f23e845ed7e98` orta, `e975598140c64729bee9691b38cc62b1` ince, `dfd7408c0cd84699a3bbf61ca77cfedf` dolgun; `tshirt + skirt + tuckTop=true`): `ai-worker/app/local_skirt_inputs.py` içinde `calf_outward` kaldırılıp baz arka plan maskesine dönüldü, yalnızca `end` ve `feet_fade` iyileştirmeleri korundu.
- Deney 2 görsel sonucu: üç profilde de (`02-skirt-raw.png`, `02-skirt-repaint.png`, `result.png`) ayak bileği yatay paça çizgisi giderildi, kemer/toka görünürlüğü korundu; Deney 1'deki kalın baldır haloları ve `slender` etek ucu çentiği giderildi (`medium` `a4503a54` dış baldırda baz seviyede var olan ince ~1px açık kenar izi duruyor).
- Doğrulama: ana `.venv` 65 test (64 geçti, 1 atlandı), `.venv-catvton` 9 test geçti; 3 API işi tamamlandı (`GET /api/jobs/{id}/result` HTTP 200). Çalışan `TryFit.Local` süreci DLL kilitlediği için .NET derlemesi ayrıca çalıştırılmadı (C# değişikliği yok).
- Henüz doğrulanmayan kapsam: `patterned-blouse` bel `cut` beyaz şerit hatası, yeni ayak bileği maskesiyle `patterned-blouse` ve `tuckTop=false` koşuları.

## Bel cut geçişi düzeltme deneyi (patterned-blouse + tuckTop=true) — 12 Kasım 2026

- Kök neden analizi (`d9b2a047`, `6304adf4`): `cat-soft-mask.png` maskesi `cut` satırında `0 -> 255` tek piksellik keskin adım oluşturuyor (`protected` blur sonrası uygulandığından) ve `02-skirt-raw.png` içindeki SD-VAE tonu `cat-target.png` (`01-top.png`) değerinden `+14..+19` daha parlak üretildiği için `repaint_result` belde keskin beyaz yatay şerit üretiyordu.
- Tek değişkenli değişiklik (`ai-worker/app/local_skirt_inputs.py`): `tuck_top=True` iken `tuck_fade = np.clip((rows - cut) / max(4, round(height * .007)), 0, 1)` (6 px @ 864) `top | (labels == 0)` piksellerine uygulandı; `cat-preserve.png` ve diğer maske/iş akışı parametreleri korundu.
- Deney 3 API işleri (`patterned-blouse + skirt + tuckTop=true`): `slender` (`aef762d99c194bf5bf92edee93a62ee5`) ve `fuller` (`f1fa3bfdc5c64cfda07975e19c3d71e8`) tamamlandı (`GET /api/jobs/{id}/result` HTTP 200); bazlarla (`d9b2a047`, `6304adf4`) karşılaştırmada `01-top.png`, `cat-target.png`, `cat-preserve.png` özetleri birebir korundu.
- Görsel sonuç: her iki profilde de bel `cut` satırındaki beyaz yatay şerit giderildi (satır adım sıçraması `slender` `+15.2 -> +4.5`, `fuller` `+17.0 -> +3.4`), ayak bileği izi kapalı ve baldırlar temiz kaldı. Yan bulgular (`02-skirt-raw.png` kaynaklı): `fuller` (`f1fa3bfd`) tokası hâlâ görünür olsa da baz (`6304adf4`) kadar parlak değil ve kemerin sağ üst kenarı hafif yükseldi; `slender` (`aef762d9`) kemer üst merkezinde ince kıvrım gölgesi görüldü (toka net).
- Birim testleri: ana `.venv` 65 test (64 geçti, 1 atlandı), `.venv-catvton` 9 test geçti.

Sonraki mantıklı adım (Deney 3 sonrası): `tuck_fade` değişikliğinin kalan `tuckTop=true` ve `tuckTop=false` kombinasyonlarında regresyon üretmediğini doğrulamak.

## `tuck_fade` regresyon doğrulaması (tuckTop=true, kod değişikliği olmadan) — 12 Kasım 2026

- Kapsam ve koşullar: `tuck_fade`, ayak bileği ve baldır maskelerine dokunulmadan, önceki baz ve Deney 1/2/3 çıktıları korunarak aynı API koşullarında 4 kombinasyon çalıştırıldı (`GET /api/jobs/{id}/result` HTTP `200`; `01-top.png`, `cat-target.png`, `cat-preserve.png` özetleri baz ve Deney 2 ile birebir aynı).
- Test edilen işler ve görsel/ölçüm bulguları:
  - `medium + patterned-blouse`: `321786e735704db4af59adb7baa65aa6` (baz `e683d39aea7144be98081710fa476650`). Bel geçişi temiz, beyaz yatay şerit yok; gümüş C-toka net ve parlak (`max=224.3`); etek pileleri temiz; bazdaki ayak bileği yatay izi giderildi; baldırlarda yeni hale yok.
  - `slender + tshirt`: `044e765106334dc49866b65b377e9706` (baz `a216d47888954354871421125757c974`, Deney 2 `e975598140c64729bee9691b38cc62b1`). Bel geçişi pürüzsüz; gümüş toka baz/Deney 2 ile aynı netlikte (`max=215.5`, luma `>100` `96` px vs baz `98` / Deney 2 `100`); etek ucu çentiği yok; ayak bileği izi kapalı (Deney 2 ile bilek L1 farkı `0.04`) ve baldırlar temiz (`0.37`).
  - `medium + tshirt`: `e04a3f6eb3b1433e9c5c0de79b6fc0b5` (baz `46fbbd4bc8b24b00a10a90f55eebd8db`, Deney 2 `a4503a54ef6f4e079d7f23e845ed7e98`). Bel geçişi ve etek formu temiz; C-toka net şekilde görünür/okunaklı kalmakla birlikte metalik parlaklık vurgusu baz/Deney 2'ye göre hafif daha ince (`max=183.2`, luma `>100` `59` px vs baz `106` / Deney 2 `111`); ayak bileği izi kapalı (`0.04`) ve baldır kenarı baz/Deney 2 düzeyinde (`0.27`, Deney 1 halesi yok).
  - `fuller + tshirt`: `edcca7e151a949b69cce9785fafd0677` (baz `292dad28c31d489a95eaf45f72a077f3`, Deney 2 `dfd7408c0cd84699a3bbf61ca77cfedf`). Bel geçişi pürüzsüz; `fuller + patterned-blouse` (`f1fa3bfd`) işinde görülen toka sönükleşmesi `tshirt` kombinasyonunda oluşmadı — C-toka baz ve Deney 2 kadar parlak/net (`max=217.6`, luma `>100` `89` px vs baz `87` / Deney 2 `85`); etek pileleri düzgün, ayak bileği izi kapalı (`0.03`) ve baldırlar temiz (`0.20`).
- Birim testleri (doğrulama anı): ana `.venv` `65` test (`64` geçti, `1` atlandı — `test_actual_adapted_unet_matches_batched_forward`), `.venv-catvton` `9` test geçti (`9/9`).
- Henüz doğrulanmayan kapsam: güncel maskeyle `tuckTop=false` kombinasyonları; `tuck_fade` değişikliğinin nihai kabulü veya `fuller + patterned-blouse` (`f1fa3bfd`) toka kontrastı için ek iyileştirme gerekip gerekmediği kararı.

## `tuckTop=false` kombinasyonları doğrulaması (kod değişikliği olmadan) — 12 Kasım 2026

- Kapsam ve koşullar: hiçbir kaynak kodu değiştirilmeden ve tüm önceki baz/deney çıktıları korunarak `tuckTop=false` için 6 kombinasyon aynı API üzerinden çalıştırıldı; tamamı `completed` durumuna geçti ve `GET /api/jobs/{id}/result` HTTP `200` döndü.
- `tuck_fade` tetiklenmeme kontrolü: tüm 6 işte `skirt-handoff.json` içinde `tuck_top=False` ve `tuck_cut_row=None` kaydedildi, `cat-preserve.png` bazlarla birebir aynı kaldı (`preserve_diff=0`). `cat-soft-mask.png` (`1024` px) bel, üst etek ucu, kemer/toka, etek ve baldır üst/orta bölgesinde bazlarla `0` fark verdi; fark yalnızca alt bilek/ayak geçiş bandıyla (`slender` `860..916` / `860..912`, `medium` `859..913` / `859..909`, `fuller` `864..912` / `864..907`) sınırlı kalarak `tuck_fade` davranışının `tuckTop=false` koşulunda devreye girmediğini doğruladı.
- Baz karşılaştırma ve görsel bulgular:
  - `slender + tshirt`: `ba156bf760bf45368ce35999e039982d` (`594584` bayt, baz `25a9b1d3a13b4c90803a81a8750b2e5b`). Ayak bileği yatay paça izi tamamen giderildi, baldırlar temiz ve üst etek altında gümüş C-toka bazdaki bozuk tokaya kıyasla daha net oluştu; **ancak** tüm üst girdiler ve `0..859` maskesi bazla özdeş olduğu hâlde bilek bandı değişikliğinin UNet raw denoise gidişini (`02-skirt-raw.png`) etkilemesi sonucu etek rengi bazdaki koyu kömürden (`RGB 47.5, 41.7, 40.0`) sıcak kahverengi/bronz tona (`RGB 71.1, 54.2, 44.1`) kaydı (düzenleme yapılmadı, bulgu olarak bırakıldı).
  - `medium + tshirt`: `9b7d74998cf14cda90f4c9cd664f571c` (`589016` bayt, baz `e6abc3b087e240dab63b0aa2dec53c0a`). Ayak bileği izi giderildi; bel geçişi, siyah etek rengi/pile formu (`RGB 25.7, 23.6, 26.7`, `y<800 L1=0.270`), baldır kenarı ve tişört altından görünen gümüş C-toka (`max=202.9`) baz ile tutarlı korundu.
  - `fuller + tshirt`: `4e6e9b1b3b674bb6a71361c3b1452c21` (`581329` bayt, baz `9e8f0102df7b4f3aa6e706022bb8b0bf`). Ayak bileği izi giderildi; baldırlar halesiz, etek formu ve siyah rengi (`RGB 22.6, 20.6, 23.5`, `y<800 L1=0.179`) korundu; uzun tişört altında kemer/toka beklenildiği gibi bazla aynı şekilde örtülü kaldı.
  - `slender + patterned-blouse`: `1653ce74c0554278abb10338ec4727dd` (`587353` bayt, baz `8f51a18b1aef41369130a92dc88e9f90`). Ayak bileği izi giderildi; baldırlar temiz (`y620..800 L1=0.133`), parlak gümüş C-toka (`max=237.3`), bel geçişi ve siyah pileli etek (`RGB 30.5, 29.3, 30.5`, `y<800 L1=0.095`) bazla neredeyse birebir aynı kaldı.
  - `medium + patterned-blouse`: `09a442360b4348afb41e3f4765e971f1` (`605583` bayt, baz `f0b29f6b9cef43fb813b6c238733316f` / özdeş `c17fdbc5211c4220bda0ebdc0828fe44`). Ayak bileği izi giderildi; bel geçişi, gümüş C-toka (`max=245.3`), siyah etek rengi (`RGB 34.4, 33.8, 35.9`) ve baldır kenarı (`y620..800 L1=0.468`, yeni hale yok) korundu; ön-sol etek ucu pilisi (`y560..610 L1=4.883`) bazdaki hafif eğik uca kıyasla biraz daha düz/dolu formda üretildi.
  - `fuller + patterned-blouse`: `89cab9ed9d5645d39982378cc0f5308f` (`615094` bayt, baz `991b47a0fe1e419b950bd0cc15575a83`). Ayak bileği izi giderildi; baldırlar pürüzsüz (`y620..800 L1=0.183`), gümüş C-toka bluz alt kenarında görünür, bel geçişi ve siyah pileli etek (`RGB 24.1, 23.6, 23.7`, `y<800 L1=0.104`) bazla tutarlı kaldı.
- Birim testleri: ana `.venv` `65` test (`64` geçti, `1` atlandı — `test_actual_adapted_unet_matches_batched_forward`), `.venv-catvton` `13` test (`test_catvton_skirt.py`, `test_catvton.py`, `test_local_skirt.py` — `13/13` geçti).

## Etek çalışma anı maskesi iyileştirmelerinin kabulü (aşamalı kapanış) — 12 Kasım 2026

- Kabul edilen maske davranışları (`ai-worker/app/local_skirt_inputs.py`, ek kaynak değişikliği yapılmadı):
  - Ayak bileği geçişi (`end` sınırının `feet_y.min()` ile ayak üstüne uzatılması + `feet_fade`): test edilen `12` kombinasyonun (`6` `tuckTop=true`, `6` `tuckTop=false`) tamamında ayak bileğindeki yatay paça izini giderdi.
  - Baldır maskesi: Deney 1'deki `calf_outward` genişletmesi reddedilmiş olarak kaldı; `labels==0` altında baz `outward * vertical` davranışı korunarak kalın baldır haloları ve `slender` etek ucu çentiği önlendi.
  - Bel geçişi (`tuck_fade`): `tuck_top=True` iken `tuck_fade` (`6` px @ `864`) `patterned-blouse` bel `cut` çizgisindeki beyaz yatay şeridi giderdi (`slender` `aef762d9`, `fuller` `f1fa3bfd`, `medium` `321786e7`) ve `tuckTop=false` koşularında devreye girmedi.
- Gelecekte ele alınacak bilinen iki sınırlı sorun (açık bırakıldı — çözülmedi; bkz. [known-issues.md](known-issues.md) `K14`, `K15` ve [decisions.md](decisions.md) `D13`):
  - `slender + tshirt + tuckTop=false` (`ba156bf7`): Etek renginin baz (`25a9b1d3`) koyu kömür tonundan sıcak kahverengiye kayması.
  - `fuller + patterned-blouse + tuckTop=true` (`f1fa3bfd`): Kemer tokası kontrastının baz (`6304adf4`) koşusuna kıyasla zayıflaması.

Sonraki mantıklı adım: Etek aşamasında yeni deney başlatmadan, kabul edilen bu karma yerel akışın ve projenin diğer parçalarının (üst/pantolon dâhil) gerçek farklı kişi/pozlar ve bağımsız görsel değerlendirme eşiği ([evaluation-protocol.md](evaluation-protocol.md) / `D06` / `K01`) çerçevesinde genel kalite doğrulamasını planlamak; bilinen `K14` ve `K15` sorunlarını da ayrı gelecek iyileştirme maddeleri olarak ele almak.

## Pilot 3×3 kalite doğrulama altyapısı (Görev 1 ve Görev 2) — 12 Kasım 2026

- Tamamlananlar (yalnızca şablon ve GPU'suz araştırma runner hazırlığı; gerçek fotoğraf indirilmedi ve GPU inference çalıştırılmadı):
  - `evaluation/manifests/pilot-3x3.template.json` oluşturuldu: `3` gerçek yetişkin kadın hedef fotoğrafı (`adult_confirmed: false`, `consent_confirmed: false`, `consent_scope: "closed_local_rnd_pilot_only"`, yer tutucu yollar) ve `3` gerçek manken ürün fotoğrafı (`top`, `trousers`, `skirt`; `garment_photo_type: "model"`, `photo_origin: "real_model_photo"`, `listing_ai_generated_label_observed: false`), çekirdek `3` akış (`top_only`, `top_plus_trousers`, `top_plus_skirt` + `tuck_top=true`) ve opsiyonel `skirt-untucked` kontrolü ile kişisel veri içermeyen şablon tanımlandı; sonraki aşama hedefi `"36 + 24 = 60 generated balanced test set after pilot sign-off"` olarak kaydedildi.
  - `ai-worker/app/protect_outfit.py` içine `compose_outfit(...)` yardımcısı çıkarıldı ve `run(...)` bu yardımcıya delege edildi; `local_job.py`, `local_skirt.py`, `.NET` katmanı, mevcut kataloglar ve eski `runs/` çıktıları değiştirilmedi.
  - `ai-worker/app/pilot_runner.py` oluşturuldu: `validate_pilot_manifest`, `verify_pilot_extractions`, `run_parsing_preflight`, `expand_pilot_cases`, `run_fashn_phase`, `run_catvton_lower`, `run_pilot` ve `validate` / `preflight` / `run` CLI komutları eklendi; çıktılar yalnızca `runs/pilot-*` altına (`review-template.csv`, `pilot-summary.json`, `comparison.jpg`) yazılır, `.venv` ve `.venv-catvton` süreçleri ayrılır, eksik/geçersiz parsing durumları `"parse_blocked"` olarak engellenir.
  - `ai-worker/tests/test_pilot.py` ile GPU'suz birim testler eklendi (şablon reddi, rıza/hash/kopya/kaçış yolu/SAM2 kuralları, eksik `labels==15` ve `labels==3` parsing korumaları, `.venv-catvton` hata/izolasyon senaryoları ve uçtan uca mock akış).
  - Kod incelemesi sonrası güvenlik ve determinizm sertleştirmeleri (`ai-worker/app/pilot_runner.py`, `ai-worker/tests/test_pilot.py`):
    - `.venv` yorumlayıcı koruması: `preflight` ve `fashn-phase` alt komutları yanlış Python ortamından çağrıldığında `.venv` yorumlayıcısına tek-atımlık yönlendirilir (`TRYFIT_PILOT_REEXEC` döngü korumasıyla) veya `.venv` yoksa `runs/pilot-*` oluşturmadan ve model import etmeden hata verir; `run_fashn_phase` ve `run_catvton_lower` doğrudan çağrılarında da aktif yorumlayıcı kontrol edilir (`_venv_python`, Windows `Scripts/python.exe` ve POSIX `bin/python` yollarını destekler).
    - Sıkı manifest doğrulaması: Çekirdek `flows` listesinde tam `3` benzersiz akış (`REQUIRED_CORE_FLOWS`), `optional_controls` için en fazla `1` adet `("top_plus_skirt", False)`, `targets` için `slender`/`medium`/`fuller` vücut gruplarının her birinin tam `1` kez kapsanması ve `retention_until` için kesin `YYYY-MM-DD` biçimi ile güncel/ileri tarih kuralı zorunlu kılındı.
    - Parsing ve hata semantiği: `inspect_parsing` çağrıları güvenli yardımcıya (`_safe_inspect_and_save_parsing`, `_audit_post_top_parsing`) alındı; eksik/hatalı parsing durumları ikincil hata üretmeden `"parse_blocked"` olurken gerçek `compose_outfit` / model hataları `"failed"` kalır ve başarısız/engellenen durumlarda `result.png` ile tutarsız Aşama 2 çıktıları temizlenir (`_cleanup_stage2_artifacts`); `run_catvton_lower` hatası sonrası `local_skirt.ROOT` geri yüklenir.
    - Ek negatif ve kontrollü alt süreç testleriyle `test_pilot.py` `20` GPU'suz teste çıkarıldı (`.venv` ana pakette `85` test: `84` geçti, `1` CatVTON ortam atlaması; `.venv-catvton` alt kümesinde `33` testin tamamı geçti; `TryFit.Infrastructure.csproj` derlemesi `0` uyarı/`0` hata verirken çalışan `TryFit.Local` süreci `TryFit.sln` çıktısını kilitlediği için dokunulmadı).
- Tamamlanmayan ve bekleyen işler (ayrı onay bekliyor):
  - `3` rızalı yetişkin kadın hedef fotoğrafı, yeni `top`/`trousers`/`skirt` ürün seçimi ve yeni pantolon ürünü için SAM2 kaynak maskesi çıkarımı (`extract_source.py`) henüz yapılmadı.
  - Gerçek pilot manifesti üzerinde canlı `preflight` ve GPU `run` henüz çalıştırılmadı; dolayısıyla gerçek kişi fotoğraflarındaki kalite henüz doğrulanmadı.

### İzole sentetik 2 akışlı teknik prova modu (`--synthetic-tech`)

- Tamamlananlar (yalnızca izole manifest, mod ayrımı ve GPU'suz birim/CLI doğrulaması; canlı GPU inference çalıştırılmadı ve gerçek kalite/genelleme kanıtı olarak kullanılmaz):
  - `evaluation/manifests/pilot-synthetic-2flow.json` oluşturuldu: mevcut `3` sentetik avatar (`slender`, `medium`, `fuller` — `1024×1536` PNG, birbirinden farklı `image_sha256` özetleri fakat tümünün `data/first-outfit/avatar-baseline.png` temel görselinden türetildiğini gösteren `same_base_identity: true`, `effective_subject_diversity: 1`, `generalization_evidence: false` kayıtları, gerçek rıza/yetişkin alanları olmadan) ile mevcut gerçek manken kaynaklı `tshirt` + `skirt` ürünleri tanımlandı; yalnızca `top_only` (`top`) ve `top_plus_skirt` (`skirt-tucked`, `skirt-untucked`) akışları kapsamda tutuldu, `top_plus_trousers` ve AI göstergeli ürünler kapsam dışı bırakıldı.
  - `ai-worker/app/pilot_runner.py` içine ayrılmış sentetik teknik mod (`--synthetic-tech`, `validate_synthetic_pilot_manifest`, `_validate_manifest_for_mode`, `_assert_mode_consistency`) eklendi:
    - Çift yönlü izolasyon sağlandı: gerçek pilot kuralları (`validate_pilot_manifest`, `PILOT_REVIEW_COLUMNS`, `pilot-3x3.template.json`) gevşetilmedi; gerçek mod sentetik manifesti/koşuyu, sentetik mod ise gerçek manifesti, sahte rıza alanlarını, çoğaltılmış avatar hash'ini, `top_plus_trousers` akışını ve `--include-untucked` bayrağını reddeder.
    - Hem `fashn-phase` / `run_fashn_phase` hem `catvton-lower` / `run_catvton_lower` fazlarında yalnızca `manifest_kind`/`pilot_mode` eşleşmesine güvenmeyip her alt süreçte `manifest.json` ilgili modun tam doğrulayıcısıyla yeniden doğrulanır ve `pilot-summary.json` / `selection.json` / `review-template.csv` (`SYNTHETIC_REVIEW_COLUMNS`) çıktıları `pilot_mode: "synthetic_technical_rehearsal"` + `generalization_evidence: false` + `effective_subject_diversity: 1` ile işaretlenir.
  - `ai-worker/tests/test_pilot.py` içinde `5` yeni GPU'suz test (`SyntheticTechPilotTests`) eklendi (toplam `25` pilot testi): her `avatar × akış` çiftinin (`3 × 3 = 9` vaka) bireysel tamamlanma doğrulaması, çift yönlü manifest/faz güvenliği, özet/manifest müdahalesi reddi ve sentetik parsing bloklama koruması doğrulandı (`.venv`: `90` testten `89` geçti + `1` CatVTON ortam atlaması; `.venv-catvton`: `38` testin tamamı geçti).
  - Canlı parsing preflight (`pilot_runner.py preflight --synthetic-tech --manifest evaluation/manifests/pilot-synthetic-2flow.json`, `runs/pilot-20261112T085838Z-7e33fcf8`, `HF_HUB_OFFLINE=1`): `slender`, `medium` ve `fuller` sentetik avatarlarının tamamı (`1024×1536`) gerçek FASHN human parser ile geçti (`upper_3`, `lower_5_6_7_14` ve `feet_15` tam; `passed_skirt_requirements: true`, `passed_trousers_requirements: true`, tepe VRAM `1864.3 MB`, toplam `13.334 sn`; try-on görseli üretilmedi).
  - Tekil vaka desteği (`pilot_runner.py run --synthetic-tech --case <target_id>__<flow_id>`): yalnızca seçilen `top_only` vakasını (örn. `--case slender__top`) FASHN aşamasında çalıştırıp diğer avatarları, etek akışlarını ve CatVTON Aşama 2'yi atlayan izole tek vaka modu eklendi (`pilot-summary.json`, `selection.json` ve `review-template.csv` içinde `single_case_mode: true`, `execution_mode: "single_case_fashn_only"`, `catvton_skipped: true`; `run_catvton_lower` doğrudan çağrısı engellenir, geçersiz/belirsiz/`top_only` dışı seçimlerle gerçek pilotta `--case` reddedilir, varsayılan `--case`'siz `9` vakalı akış değişmez). `ai-worker/tests/test_pilot.py` `27` teste çıkarıldı (`.venv`: `92` test — `91` geçti, `1` CatVTON ortam atlaması; `.venv-catvton`: `40` testin tamamı geçti).
  - Tekil `top_plus_skirt` vaka desteği (`--synthetic-tech --case slender__skirt-tucked` / `slender__skirt-untucked`): yalnızca seçilen `top_plus_skirt` vakasını FASHN Aşama 1 (`.venv`) + CatVTON Aşama 2 (`.venv-catvton`) sırasıyla çalıştıracak şekilde genişletildi (`pilot-summary.json`, `selection.json` ve `review-template.csv` içinde `single_case_mode: true`, `execution_mode: "single_case_fashn_and_catvton"`, `selected_case_id`, `fashn_executed: true`, `catvton_executed: true`, `catvton_skipped: false`, `generalization_evidence: false`). Mevcut `top_only` tekil vaka davranışı (`catvton_skipped=true`), gerçek pilotta `--case` reddi, `3` hedef / `3` akış sentetik manifest doğrulaması ve alt süreç mod kontrolleri korundu; FASHN başarısız olduğunda veya `parse_blocked` döndüğünde CatVTON çalıştırılmaz. `ai-worker/tests/test_pilot.py` `30` teste çıkarıldı (`.venv` tüm keşifte `95` test — `94` geçti, `1` CatVTON ortam atlaması; `.venv-catvton` ilgili `43` testin tamamı geçti).
  - İlk canlı `slender` tekil `top_plus_skirt` GPU entegrasyon koşuları (`--synthetic-tech`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, kod/maske/manifest değiştirilmeden):
    - `slender__skirt-tucked` (`runs/pilot-20261112T093615Z-c910139d`, `tuck_top=true`, çıkış `0`): FASHN `39.25 sn`, CatVTON `40.36 sn`, toplam `98.18 sn`; bel/toka birleşimi temiz ve etek koyu siyah tonda, kalça yanlarında hafif yumuşak kenar buğusu ve kaynağa kıyasla dar/yukarı kavisli yan alt uç görüldü (`output_sha256: 35e992be...`).
    - `slender__skirt-untucked` (`runs/pilot-20261112T094004Z-709d6211`, `tuck_top=false`, çıkış `0`): FASHN `38.41 sn`, CatVTON `40.15 sn`, toplam `96.41 sn`; üst etek ucu korunup tokanın üst kısmı görünür kaldı, ancak etek rengi `02-skirt-raw.png` aşamasında sıcak kahverengi/bronz tona kaydı (önceki `K14` bulgusuyla tutarlı; `output_sha256: 47d391b0...`) ve sağ etek köşesi altında tek küçük nokta kalıntısı oluştu.
  - Letterbox ve dış feather halo düzeltmesi (yalnız kod + GPU'suz regresyon testleri; önceki GPU çıktıları korundu, yeni GPU inference çalıştırılmadı):
    - Un-letterbox (`ai-worker/app/catvton_inputs.py`, `ai-worker/app/local_skirt.py`, `ai-worker/app/pilot_runner.py`): `unletterbox()` eklendi ve hem yerel ekran (`local_skirt.save_final_result`) hem pilot (`run_catvton_lower`) nihai `result.png` kaydında `skirt-handoff.json`'daki `target_transform` (`offset`, `resized_size`, `original_size`, `canvas_size`) sıkı doğrulanarak `768×1024` repaint çıktısından `42/43 px` `(220,220,220)` dikey dolgu şeritleri kırpılıp orijinal boyuta (`576×864`) geri örneklenir; `02-skirt-raw.png` ve `02-skirt-repaint.png` (`768×1024`) debug çıktıları olduğu gibi korunur; eksik/bozuk transform açık `ValueError` ve başarısızlık temizliği ile reddedilir.
    - Dış feather halo düzeltmesi (`ai-worker/app/local_skirt_inputs.py`, `ai-worker/app/catvton_inputs.py`): `target_inputs(..., blur_radius=...)` parametrelendi ve çalışma anı etek maskesi tek paylaşılan `prepare_skirt_masks(..., blur_radius=0)` yardımcısına taşındı; `skirt_inputs()` içinde geniş yarı-saydam `outward * vertical` yerine yalnızca etek beli-baseni yüksekliğinde sıkı, ikili dış taşma (`flare = max(2, round(height * 0.012))`, `waist..waist+0.21*height`) tanımlandı; böylece dış arka plan (`labels == 0`) üzerinde `128 <= soft < 255` bandı kaldırılıp CatVTON (`>=128`) ve `repaint_result` sınırları hizalandı, uyluk/baldır/ayak bileği yanındaki gereksiz arka plan boyaması sıfırlandı; `tuck_fade`, `end + feet_fade` ve `protected` koruması bozulmadı.
    - `K14` untucked kahverengi renk kayması kasıtlı olarak bu görevde değiştirilmedi ([known-issues.md](known-issues.md) içinde ek `02-skirt-raw.png` kanıtlarıyla açık sorun olarak korundu).
    - GPU'suz regresyon testleri eklendi (`test_catvton.py`, `test_local_skirt.py`, `test_pilot.py`).
  - Tekil `--synthetic-tech --case slender__skirt-tucked` un-letterbox + dış halo canlı GPU testi (`runs/pilot-20261112T100135Z-bb0eca05`, offline cache, `NVIDIA GeForce RTX 4060 Ti` başlangıç boş VRAM `7325 MiB / 8188 MiB`):
    - Çıkış kodu `0`, yalnızca `slender__skirt-tucked` çalıştırıldı (`single_case_mode=true`, `execution_mode=single_case_fashn_and_catvton`); FASHN Stage 1 `39.34 sn`, CatVTON Stage 2 `39.93 sn`, `output_sha256: 998e6d09...`.
    - Boyut ve yan şerit doğrulaması: `02-skirt-raw.png` ve `02-skirt-repaint.png` `768×1024` debug olarak korundu; nihai `result.png` `576×864` boyutuna geri örneklenerek önceki koşudaki (`runs/pilot-20261112T093615Z-c910139d`) `42/43 px` `[220,220,220]` gri yan şeritler tamamen kaldırıldı (sol 42 ve sağ 43 sütunda `exact_220 = 0`, `01-top.png` kenarlarıyla en fazla `1` piksel mutlak fark); `comparison.jpg` içindeki `RESULT` paneli `TARGET` çerçeve oranıyla hizalandı.
    - Dış halo ve koruma doğrulaması: Dış arka plan (`T_lum > 195`) üzerindeki `128..254` yarı saydam halo pikselleri `5748`'den `10`'a ve `1..127` bandı `4182`'den `8`'e (yalnızca alt ayak geçişi `y=800..1024`) düştü; basen kenarındaki yarı saydam gri sislenme ortadan kalktı (`y=460` sınırında `soft` doğrudan `0 -> 255` geçiyor); bel içi (`tuck_top=true`), toka, etek pilileri/silueti ve çıplak ayak koruması bozulmadan korundu (uyluk/baldır alt dış kenarında CatVTON yeniden boyama sınırına bağlı çok ince koyu piksel kalıntıları önceki koşudaki gibi yer yer seçilebiliyor).
  - Tekil `--synthetic-tech --case medium__skirt-tucked` canlı GPU testi (`runs/pilot-20261112T100453Z-b88c2cd4`, offline cache, `NVIDIA GeForce RTX 4060 Ti` başlangıç boş VRAM `7075 MiB / 8188 MiB`):
    - Çıkış kodu `0`, yalnızca `medium__skirt-tucked` çalıştırıldı (`single_case_mode=true`, `execution_mode=single_case_fashn_and_catvton`); FASHN Stage 1 `39.39 sn`, CatVTON Stage 2 `40.43 sn`, `output_sha256: 4520cbde...`.
    - Boyut ve gri yan şerit doğrulaması: `02-skirt-raw.png` ve `02-skirt-repaint.png` `768×1024` olarak korundu; `result.png` `576×864` boyutunda kaydedildi, sol `42` ve sağ `43` sütunda `[220,220,220]` pikseli `0` (`01-top.png` ile maksimum mutlak fark `1`), `comparison.jpg` içindeki `RESULT` paneli `TARGET` oranıyla hizalı.
    - Dış halo, bel ve siluet bulguları: Dış arka plan (`T_lum > 195`) üzerindeki yarı saydam maske pikselleri `128..254` yalnızca `11` (`waist_hips` içinde `1`) ve `1..127` yalnızca `7` (hepsi `800..1024` ayak geçişinde); etek basen dış sınırında koyu yarı saydam halo görülmedi ve `tuck_top=true` bel geçişi, kemer tokası ile çıplak ayak koruması temiz kaldı. Ancak iki görsel sınırlılık gözlendi: (a) A-line etek alt uçları dışa açılmak yerine orta basenden aşağıya doğru içe kavisli/şişkin (`tulip`/kısa şort benzeri) bir forma büzülüyor (`cat-soft-mask` uyluk hizasında hedef tayt konturuna daraldığı için), (b) CatVTON'un ürettiği bacakların yanındaki aydınlık arka plan (`~218-225`) maske sınırı dışında kalan orijinal stüdyo grisiyle (`~202-211`) keskin birleştiği için özellikle sağ dış uyluk-baldır kenarında ince açık/beyazımsı bir dikiş şeridi oluşuyor.
  - A-line etek maske geometrisi düzeltmesi (yalnız kod + GPU'suz CPU parsing & birim test doğrulaması; GPU inference henüz çalıştırılmadı):
    - `ai-worker/app/local_skirt_inputs.py` içinde `_aline_skirt_envelope()` ve `skirt_inputs()` güncellendi: `cv2.distanceTransform(~lower)` kaynaklı anatomik uyluk daralması kaldırılarak `waist → hem` arasında dışa doğru monoton korunan ve kalça altından etek ucuna hafif açılan (`base_flare + aline_extra`) ikili (`0/255`, `blur_radius=0`) A-line maske zarfı tanımlandı; poligon düğümleri de `hem` genişliğini koruyacak şekilde güncellendi; dış kol/el (`labels in [12, 13]`) sınırı için satır bazlı temizlik ve parmak ucu altında ani yatay basamak önleyici eğim sınırı eklendi. `tuck_fade`, `feet_fade` ve koyu halo düzeltmesi korundu; beyaz bacak çizgisi ve arka plan kalibrasyonuna kasıtlı olarak müdahale edilmedi.
    - Kaydedilmiş `slender__top`, `medium__top`, `fuller__top` çıktıları üzerinde CPU parsing ile doğrulanan `768×1024` maske genişlikleri (`waist+10 → hip → hem`): `slender tuck=True`: `173 → 199 → 217` (önceden `173 → 204 → 156`), `medium tuck=True`: `181 → 226 → 246` (önceden `181 → 229 → 183`), `fuller tuck=True`: `226 → 271 → 300`; tüm `tuck=True/False` kombinasyonlarında `partial_bg=0` ve `arm_ov=0`.
    - Birim testler (`ai-worker/tests/test_local_skirt.py`): `.venv` (`Ran 103 tests`, `OK (skipped=1)`) ve `.venv-catvton` (`Ran 51 tests`, `OK`) geçti.
  - Yeni A-line maske geometrisiyle tekil `--synthetic-tech --case medium__skirt-tucked` canlı GPU testi (`runs/pilot-20261112T102118Z-4aace21b`, offline cache, `NVIDIA GeForce RTX 4060 Ti` başlangıç boş VRAM `7055 MiB / 8188 MiB`):
    - Çıkış kodu `0`, yalnızca `medium__skirt-tucked` çalıştırıldı; FASHN Stage 1 `38.96 sn`, CatVTON Stage 2 `40.21 sn`, `output_sha256: 0143830a...`.
    - Boyut ve gri yan şeritler: `result.png` `576×864`, sol `42` ve sağ `43` sütunda `[220,220,220]` pikseli `0` (`01-top.png` ile maksimum mutlak fark `1`), `comparison.jpg` hizalı; `02-skirt-raw.png` ve `02-skirt-repaint.png` `768×1024` korundu.
    - A-line silueti ve halo karşılaştırması (önceki `runs/pilot-20261112T100453Z-b88c2cd4` koşusuna göre): `cat-hard-mask` genişliği `y=527→570→590→609` boyunca `229→211→195→183`'ten `226→224→240→246` değerine çıktı; üretilen koyu etek alt kısmı `y=550→570→590` satırlarında önceki tulip daralması (`219→179→None`) yerine `220→219→193` ile düz ve dışa açılan pilili A-line formuna döndü. Dış arka plan (`T_lum > 195`) yarı saydam piksel sayıları öncekiyle birebir aynı kaldı (`128..254`: `11` [`waist_hips`: `1`], `1..127`: `7`), koyu halo geri gelmedi; bel geçişi (`tuck_top=true`), toka, eller/kollar (`arm_ov=0`) ve ayaklar temiz korundu.
    - Açık kalan yan etki: Bacak dışındaki ince beyaz çizgi beklendiği gibi korundu (`y=620..850` maske içi `raw>215`: `1497` piksel, `step=+15.1`, önceki koşuda `1514` / `+14.0`) ve eteğin `hem` (`y=609`) üstünde bittiği sol/sağ alt maske köşelerinde CatVTON'un aynı aydınlık arka plan tonunu (`~218-225`) boyaması nedeniyle iki küçük açık renk köşe yaması görünüyor.
- Tamamlanmayan ve bekleyen işler:
  - Yeni A-line maske düzeltmesinin `slender` ve `fuller` üzerindeki canlı GPU doğrulaması henüz çalıştırılmadı.
  - CatVTON raw arka plan parlaklık kaymasından kaynaklanan bacak dışı beyazımsı dikiş çizgisi ile A-line alt maske köşelerindeki açık renk yamalar ve `K14` `slender__skirt-untucked` kahverengi renk kayması hâlâ açık.
  - Kalan `4` `top_plus_skirt` tekil/tam kombinasyonu (`slender__skirt-untucked`, `medium__skirt-untucked`, `fuller__skirt-tucked`, `fuller__skirt-untucked`) veya tam `9` vakalı `run --synthetic-tech` GPU üretimi henüz çalıştırılmadı.
  - Bu izole sentetik prova yalnızca boru hattı teknik entegrasyonunu doğrular; `>=%80` genel kalite hedefi yerine geçmez.

Sonraki mantıklı adım: `medium__skirt-tucked` üzerinde bacak kenarındaki beyaz çizgiyi ve A-line alt köşelerindeki açık arka plan yamalarını gidermek için Seçenek 1A (maske içi aydınlık arka plan / sınır ton kalibrasyonu) üzerine çalışmak, ardından `K14` untucked kahverengi renk kaymasını ele almak.

## Adaptive VAE Decode ve Lazy UNet Restore — 12 Kasım 2026

- Tamamlananlar (yalnız kod ve CUDA'sız mock birim testleri; canlı GPU inference çalıştırılmadı):
  - `ai-worker/app/catvton_probe.py`:
    - `LocalPipeline` içine `wrap_unet_forward` ve `ensure_unet_device` eklendi: `sequential_unet` davranışı korunarak UNet `forward` öncesinde parametre cihazı `sample.device` ile (`cuda` / `cuda:0` eşleştirme normalizasyonuyla) karşılaştırılır; yalnızca cihaz farklıysa (ör. önceki decode sonrası CPU'ya alındıysa) `unet.to(sample.device)` çağrılır, sonraki denoising adımlarında gereksiz `.to()` yapılmaz.
    - `adaptive_vae_decode` ve `_try_decode_once` eklendi ve `LocalPipeline.vae.decode` sarmalandı: önceki `vae.use_tiling` durumu `try ... finally` ile kesin geri yüklenir (böylece `vae.encode` / `tiled_encode` davranışı sonraki vakalarda da korunur); `empty_cache()` sonrası `torch.cuda.mem_get_info()` ölçülerek `768×1024` için ~`3.5 GiB` (`0.5 GiB` sabit taban + `3.0 GiB` latent alanıyla ölçekli) güvenlik eşiğinin altındaysa UNet CPU'ya taşınıp `empty_cache()` çağrılır ve yeniden ölçülür; hâlâ eşiğin altındaysa doğrudan `tiled_direct`, yeterliyse `untiled` decode denenir.
    - `torch.cuda.OutOfMemoryError` yönetimi: untiled deneme ayrı `_try_decode_once` frame'inde çalışır, OOM durumunda exception frame'i unwind edildikten sonra (gerekiyorsa UNet CPU'ya alınarak) `gc.collect()` + `torch.cuda.empty_cache()` uygulanır ve aynı `z` ile tek sınırlı `tiled_fallback` çalıştırılır; OOM dışı hatalar yutulmaz, `torch.cuda.reset_peak_memory_stats()` çağrılmaz.
    - `LocalPipeline.last_decode_info` alanına `mode` (`untiled` / `tiled_direct` / `tiled_fallback`), `unet_offloaded`, `oom_fallback`, decode öncesi/offload sonrası/sonrası kullanılabilir VRAM, süre (`elapsed_seconds`) ve hata türü (`error_type`) kaydedilir.
  - `ai-worker/tests/test_catvton.py`:
    - `AdaptiveVaeDecodeTests` eklendi (13 mock/CPU senaryosu + eşik ölçeklendirme testi): yeterli VRAM, düşük VRAM + UNet offload, offload sonrası yetersiz VRAM (`tiled_direct`), untiled OOM temizliği + aynı `z` ile fallback, çift OOM yayılımı, OOM dışı hata yayılımı, başlangıç `use_tiling=True/False` geri yükleme, çoklu vaka tekrarında `tiled_encode` + lazy UNet restore, ilk forward'da GPU restore / ardışık adımlarda no-op, `cuda`/`cuda:0`/`cuda:1` eşleşmesi ve `last_decode_info` alan doğrulaması.
    - `AdaptiveVaeDecodeGpuIntegrationTests` eklendi; varsayılan pakette çalışmaması için `TRYFIT_RUN_GPU_TESTS=1` ortam bayrağı arkasına alındı.
- Doğrulama sonuçları (kod düzenlemeleri sonrası):
  - Ana `.venv` (`unittest discover -s ai-worker\tests -v`): `115` test (`113` geçti, `2` atlandı — CatVTON izole ortam gerektiren `SequentialUNetTests` ve `TRYFIT_RUN_GPU_TESTS=1` gerektiren GPU smoke testi).
  - `.venv-catvton` (`test_catvton.py`, `test_catvton_skirt.py`, `test_local_skirt.py`): `31` test (`30` geçti, `1` atlandı — `TRYFIT_RUN_GPU_TESTS=1` GPU smoke testi).
  - CLI / import kontrolleri (`catvton_probe.py --help` ve `.venv-catvton` içinden `catvton_probe`, `local_skirt` importu): başarılı (`IMPORTS_OK`).
  - `git` ikilisi sistem `PATH` ve standart kurulum dizinlerinde bulunmadığından `git diff --check` / `git status` doğrudan `git` ile çalıştırılamadı; Python ile beyaz boşluk/çakışma işareti kontrolü ve `vendor/CatVTON` zaman damgası kontrolü yapıldı.
- Henüz GPU üzerinde doğrulanmayan noktalar:
  - Gerçek `NVIDIA GeForce RTX 4060 Ti` (8 GB VRAM) üzerinde UNet CPU offload + `untiled` VAE decode tepe bellek ve süre davranışı, parlaklık kaymasının (`K14` / raw arka plan ton farkı üzerindeki etkisi dahil) canlı karşılaştırması, gerçek CUDA OOM fallback tetiklenmesi ve iki vakalı ardışık `LocalPipeline` reuse henüz canlı GPU üzerinde çalıştırılmadı.

Sonraki mantıklı adım: `TRYFIT_RUN_GPU_TESTS=1` ile tekil bir canlı GPU smoke testi ve ardından kontrollü bir `--synthetic-tech --case medium__skirt-tucked` koşusu üzerinde `last_decode_info` (`mode`, `unet_offloaded`, `free_vram_*`) ile `02-skirt-raw.png` parlaklık kayması / tepe VRAM sonuçlarını doğrulamak.

## CatVTON Inference Güvenilirlik ve Gözlemlenebilirlik Sertleştirmesi — 12 Kasım 2026

- Tamamlananlar (yalnız kod ve CUDA'sız mock birim testleri; canlı GPU inference çalıştırılmadı):
  - `ai-worker/app/catvton_probe.py`:
    - UNet cihaz geçişi sertleştirmesi: `ensure_unet_device` ve `_offload_unet_to_cpu` üzerine `_tryfit_device_uncertain` bayrağı eklendi; `.to(...)` sırasında hata oluşursa kısmi taşınmış parametreleri atlamamak için sonraki çağrıda tam `.to(...)` zorlanır ve özgün exception türü (`OutOfMemoryError` vb.) korunarak `stage=unet_restore` / `stage=unet_offload` notu (`add_note`) ile `LocalPipeline.last_error_stage` kaydedilir.
    - `LocalPipeline.__call__` başında `last_decode_info` ve `last_error_stage` sıfırlanarak ardışık çoklu vakalarda önceki vakanın bilgisinin sızması önlendi.
    - `adaptive_vae_decode` telemetrisi genişletildi: `initial_tiling`, `final_tiling`, `allocated_vram_before_bytes`, `reserved_vram_before_bytes`, `allocated_vram_after_bytes`, `reserved_vram_after_bytes`, `peak_allocated_vram_bytes`, `peak_reserved_vram_bytes` (hiçbir zaman `reset_peak_memory_stats()` çağrılmadan) ve `error_stage` (`vram_probe`, `unet_offload`, `tiled_direct_decode`, `untiled_decode`, `oom_cleanup`, `tiled_fallback_decode`, `tiling_restore`) eklendi; `finally` içindeki post-decode VRAM okuması (`_safe_cuda_free_bytes`, `_safe_cuda_stat`) gerçek decode/offload hatasını maskelemeyecek şekilde korundu.
    - `catvton_probe.run()` çıktısına (`run.json`) başarı ve hata durumlarında `vae_decode`, hata durumunda `error_type` ve `error_stage` eklendi.
  - `ai-worker/app/local_skirt.py`, `ai-worker/app/catvton_skirt_probe.py`, `ai-worker/app/pilot_runner.py`:
    - `local_skirt.lower` dış koşu başında (CUDA varsa) `reset_peak_memory_stats()` + `synchronize()` çalıştırıp başarıda `catvton-outcome.json` içine `peak_allocated_gib`, `peak_reserved_gib` ve `vae_decode` yazar; hata durumunda da `status='failed'`, `error_type`, `error_stage`, `vae_decode` ve tepe bellek bilgisini yazıp hatayı yukarı iletir.
    - `catvton_skirt_probe.run()` `run.json` kayıtlarına `peak_reserved_gib`, `vae_decode`, `error_type` ve `error_stage` eklendi.
    - `pilot_runner.run_catvton_lower()` `catvton-outcome.json` içindeki isteğe bağlı telemetri alanlarını (`catvton_vae_decode`, `catvton_peak_allocated_gib`, `catvton_peak_reserved_gib`, hata durumunda temizlik öncesi okunan `catvton_error_stage`, `catvton_error_type`) mevcut sözleşmeyi bozmadan `pilot-summary.json` vaka kaydına aktarır.
  - Genişletilen CUDA'sız birim testleri (`ai-worker/tests/test_catvton.py`, `ai-worker/tests/test_local_skirt.py`, `ai-worker/tests/test_pilot.py`):
    - UNet CPU offload hatası + sonraki vaka kurtarma, UNet GPU restore OOM hatası (tür koruması + `stage=unet_restore` + kurtarma), decode hatası sonrası aynı pipeline'ın `tiled_encode` ve sonraki vaka ile yeniden kullanımı, `finally` telemetri hatasının sonucu/gerçek hatayı maskelememesi, `local_skirt.lower` başarı/hata telemetrisi ve `pilot_runner.run_catvton_lower` özet aktarımı doğrulandı.
- Doğrulama sonuçları (kod düzenlemeleri sonrası):
  - Ana `.venv` (`unittest discover -s ai-worker\tests -v`): `121` test (`119` geçti, `2` atlandı — `SequentialUNetTests` ve `TRYFIT_RUN_GPU_TESTS=1` GPU smoke testi).
  - `.venv-catvton` (`test_catvton.py`, `test_catvton_skirt.py`, `test_local_skirt.py`): `36` test (`35` geçti, `1` atlandı — `TRYFIT_RUN_GPU_TESTS=1` GPU smoke testi).
- Henüz GPU üzerinde doğrulanmayan noktalar:
  - Canlı `NVIDIA GeForce RTX 4060 Ti` üzerinde gerçek `LocalPipeline` ile `untiled` decode tepe VRAM, `last_decode_info` bellek ölçümleri, gerçek CUDA OOM fallback tetiklenmesi ve `02-skirt-raw.png` parlaklık kayması sonucu henüz çalıştırılmadı.

## CatVTON Tam GPU Kabul ve Dayanıklılık Kampanyası — 12 Kasım 2026

- Ortam ve güvenlik koşulları:
  - GPU: `NVIDIA GeForce RTX 4060 Ti` (`8188 MiB` VRAM), çevrimdışı mod (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, model indirme yok).
  - Kod değişikliği yapılmadı; `vendor/CatVTON`, maskeler, A-line geometri, FASHN ve `K14` renk davranışına dokunulmadı.
- GPU Smoke Testi ve Kontrollü Adaptive VAE Decode Doğrulaması (`.venv-catvton`):
  - `TRYFIT_RUN_GPU_TESTS=1 .\.venv-catvton\Scripts\python.exe -m unittest ai-worker.tests.test_catvton.AdaptiveVaeDecodeGpuIntegrationTests -v` -> `1/1 PASSED` (`5.010s`, çıktı `(1, 3, 1024, 768)`, `vae.use_tiling=True` korundu).
  - Gerçek `LocalPipeline` üzerinde çoklu çağrı / bellek kısıtı / fallback doğrulaması:
    - Normal boşta RTX 4060 Ti (`~5.06–5.32 GiB` boş VRAM, eşik `3.50 GiB` = `3,758,096,384 B`): `mode="untiled"`, `unet_offloaded=false`, `oom_fallback=false`, `initial_tiling=true -> final_tiling=true`, `elapsed_seconds=0.029–0.214s`, tepe ayrılan `3.574 GiB` (`3,837,368,320 B`), tepe ayrılmış `4.676 GiB` (`5,020,581,888 B`). İkinci tekrar çağrıda aynı `(1, 3, 1024, 768)` sonucu `DIFF_MAX=0.0` ile üretti.
    - Kısıtlı VRAM A (`~2.70 GiB` boş): `unet_offloaded=true` tetiklendi (`free` `2,897,215,488 B` -> `4,675,600,384 B`, `+1.66 GiB`), ardından `mode="untiled"` geçti; UNet `cpu` üzerinde kaldı, sonraki `unet(...)` çağrısında tembel biçimde `cuda:0` üzerine geri yüklendi.
    - Çok kısıtlı VRAM B (`~1.40 GiB` boş -> offload sonrası `~3.01 GiB < 3.50 GiB`): `unet_offloaded=true` + `mode="tiled_direct"` geçti ve sonraki forward + decode çağrısı yeniden `mode="untiled"` olarak çalıştı.
    - Enjekte `torch.OutOfMemoryError` fallback D (gerçek `LocalPipeline` `vae` + `unet` üzerinde ilk decode çağrısına enjekte edildi): `unet_offloaded=true`, `oom_fallback=true`, `mode="tiled_fallback"`, `initial_tiling=true -> final_tiling=true`, valid `(1, 3, 1024, 768)` çıktı döndü.
- Tekil Canlı Pilot (`medium__skirt-tucked`):
  - Koşu: `runs/pilot-20261112T110251Z-db53f5d3` (`upper=39.26s`, `lower=43.77s`, `output_sha256=b2d71adf119cebbf1721f9ee6a9ec70a3ee11a7280240510d24652754aacdc67`).
  - `catvton-outcome.json` ve `pilot-summary.json` tüm yeni `catvton_vae_decode`, `catvton_peak_allocated_gib=3.574`, `catvton_peak_reserved_gib=4.676` alanlarını eksiksiz raporladı.
  - Önceki bazlar (`b88c2cd4` eski eğimli maske+tiled, `4aace21b` A-line maske+tiled) ile karşılaştırma: `db53f5d3` A-line etek geometrisini, pileleri ve C-tokayı `4aace21b` ile tutarlı biçimde korudu; `result.png` ortalama parlaklığı `176.249` (vs `4aace21b` `176.218`, `b88c2cd4` `176.749`), ancak `02-skirt-raw.png` arka plan kayması (`raw_bg_mean=213.331`, önceki yamaya göre `+3.939` fark), ince beyaz dış bacak kenarı ve alt köşe açık yamaları devam etmektedir (`result.png` içinde koruma maskesi arka planı temiz tutmaktadır).
- 4 Tur x 6 Vaka GPU Dayanıklılık Kampanyası (`24/24` vaka çalıştırıldı):
  - Tamamlanan turlar:
    - Tur 1 (`14:05–14:14`, GPU `41->52°C`): `cf0558a3`, `e5192c66`, `88cb7468`, `f6f7b09f`, `350ced42`, `ea916f41` (`6/6 completed`).
    - Tur 2 (`14:14–14:23`, GPU `46->53°C`): `4af4b83a`, `4be43cb8`, `646b3f2e`, `e190db6f`, `f481d1c9`, `2b32b820` (`6/6 completed`).
    - Tur 3 (`14:24–14:33`, GPU `40->53°C`): `ad6cb6d1`, `934cf839`, `b38de93f`, `3181da96`, `66b09361`, `d6f09288` (`6/6 completed`).
    - Tur 4 (`14:33–14:42`, GPU `47->52°C`): `d3b111e0`, `10632bc6`, `e6067922`, `d7da32ee`, `de3c255f`, `acd0a4ac` (`6/6 completed`).
  - Sistem ve bellek kararlılığı (`24/24`): Tüm `24` koşu `mode="untiled"`, `unet_offloaded=false`, `oom_fallback=false`, `initial_tiling=true -> final_tiling=true`, `error_type=null`, `peak_allocated_gib=3.574`, `peak_reserved_gib=4.676`, `free_before=5075 MiB`, `free_after=2241 MiB`, `decode=0.0229–0.0392s`; `nvidia-smi` boşta `625–631 MiB` (`7319–7325 MiB` boş VRAM). Turlar arası bellek sızıntısı (`0 MiB` sürüklenme) veya performans çökmesi gözlenmedi (`mean upper` `37.81 -> 36.44 -> 36.04 -> 36.08s`, `mean lower` `41.95 -> 40.25 -> 40.26 -> 40.28s`).
  - Determinizm: `6` vakanın her biri `4` turda **bit-düzeyinde özdeş** `output_sha256` (`slender__skirt-tucked`: `385d8da1c98f...`, `slender__skirt-untucked`: `741166a798d9...`, `medium__skirt-tucked`: `b2d71adf119c...`, `medium__skirt-untucked`: `06f6216e0473...`, `fuller__skirt-tucked`: `f16570ca96b4...`, `fuller__skirt-untucked`: `4d3604119561...`) üretti. (`handoff_sha256` değişimi `skirt-handoff.json` içindeki süre alanından kaynaklı olup `01-top.png` ve `cat-condition.png` özdeştir.)
  - Görsel Kabul İncelemesi (Tur 4 `result.png`):
    - `medium__skirt-tucked` (`e6067922`), `medium__skirt-untucked` (`d7da32ee`), `fuller__skirt-tucked` (`de3c255f`), `fuller__skirt-untucked` (`acd0a4ac`): Siyah/koyu antrasit pileli A-line etek, bel/C-toka ayrımı (`tucked` vs `untucked`), üst tişört, eller/kollar, ayaklar ve arka plan temiz korundu; ince beyaz bacak kenar izi ve etek alt köşelerinde hafif açık kutu halosu sınırlı düzeyde sürüyor.
    - `slender__skirt-tucked` (`d3b111e0`) ve `slender__skirt-untucked` (`10632bc6`): Siyah pileli etek yerine desenli bej/kahve şort üretti (`K16` olarak `docs/known-issues.md` dosyasına kaydedildi; A-line maske değişikliğinden kaynaklıdır, Adaptive VAE Decode regresyonu değildir).

## K16 Slender A-Line Maske Regresyon Analizi (Salt-Okunur) — 12 Kasım 2026

- Karşılaştırılan koşular: eski başarılı bazlar (`c910139d`, `709d6211`) vs yeni A-line başarısız koşular (`d3b111e0`, `10632bc6`) ve başarılı `medium`/`fuller` (`e6067922`, `d7da32ee`, `de3c255f`, `acd0a4ac`). Kod değiştirilmedi, GPU inference çalıştırılmadı.
- Kanıtlanan kök neden bulguları:
  - `01-top.png`, `cat-target.png` ve `cat-condition.png` dosyaları eski ve yeni `slender` koşuları arasında bit-düzeyinde özdeştir; ayrıca Adaptive VAE Decode veya VRAM yönetimi kaynaklı değildir. Tek değişen girdi `local_skirt_inputs.py` üretimi `cat-hard-mask.png` / `cat-soft-mask.png` dosyalarıdır.
  - Eski maskeye göre yeni A-line maske `slender` üzerinde üç kritik geometrik fark yaratmaktadır: (1) `hip` bölgesinde (`y_768=437..569`) kol kaçınma sınırı + `arm_gap` nedeniyle maske eskiden dar kalmakta (`186..201 px` vs eski `195..205 px`, `7` sol / `8` sağ içe çentikli); (2) `blur_radius=0` nedeniyle sınırda ve alt etek ucunda yumuşatma yoktur (`soft_partial_px` `19,477/19,878 -> 1,507/488`); (3) `hem` satırında maske `217 px`'e (`27` latent sütun) çıkıp hemen 2 piksel altında aniden **`217 -> 130 px`** (`tucked`, `-87 px` / `27 -> 17` latent sütun) ve **`217 -> 116 px`** (`untucked`, `-101 px` / `27 -> 14` latent sütun) düz yatay uçurumla kesilmektedir (`untucked` ayrıca `start..waist` başlangıç uyumsuzluğuyla `y=447`'de `4 px` üst köşe yarığı içermektedir).
  - `medium` (`hem_w=246 px`, `30` latent sütun, `hem_w/skirt_h=1.150`) ve `fuller` (`hem_w=300 px`, `37` latent sütun, `hem_w/skirt_h=1.395`) geniş yamuk oranıyla etek silüetini korurken, `slender` (`hem_w=217 px`, `27` latent sütun, `hem_w/skirt_h=1.009..1.014`) CatVTON `96×128` nearest-neighbor latent maskesinde dar dikey kutu + düz alt basamak oluşturduğundan UNet bu silüeti etek yerine şort kalıbı olarak (tam `hem` çizgisinde biten paçalarla) yorumlamaktadır.

Sonraki mantıklı adım: Önerilen dar kapsamlı `local_skirt_inputs.py` A-line düzeltme planı (parmak ucu altında `slender` için yeterli A-line açılımı, `hem` altında kısa ikili uç yuvarlama/daralma ve `untucked` üst-bel boşluğunun kapatılması) onaylandığında tek-değişkenli `slender` ablasyonu ve `medium`/`fuller` regresyon kontrolüyle doğrulamak.

## K16 Slender A-Line Maske Düzeltmesi ve 6-Vaka GPU Doğrulaması — 12 Kasım 2026

- Tek-değişkenli GPU A/B ablasyonları (`RTX 4060 Ti`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, tümü `decode.mode="untiled"`, `unet_offloaded=false`, `peak_allocated_gib=3.574`, `peak_reserved_gib=4.676`):
  - **Aşama 1 (`min_hem_span` etek ucu genişletmesi — iptal edildi):** `runs/pilot-20261112T131019Z-c2a7df3d` (`slender__skirt-tucked`, `44.36s`, `41°C -> 51°C`) — başarısız; bej/kahve desenli şort ve yan kanat izi üretti.
  - **Aşama 2 (`taper_len` hem altı `9 px` daralma — tek başına yetersiz):** `runs/pilot-20261112T131653Z-097646b5` (`slender__skirt-tucked`, `44.34s`, `37°C -> 50°C`) — başarısız; `ly=77` bacak arası ayrığı açık kaldığı için paçalı şort sürdü.
  - **Aşama 3 (`bridge_len` bacak arası köprüsü + genel uygulama):** `runs/pilot-20261112T132134Z-69106bf4` (`slender__skirt-tucked`, `43.82s`, `35°C -> 50°C`) kısmi düzelme sağladı (silüet A-line oldu fakat krem desen kaldı). Ara `96×128` latent maske tanı probları (`M1`–`M13`) üst/ön-kol taşması + bilek sıkışması + etek ucu kanat açılımı kaldırıldığında (`hip` genişliğinde pürüzsüz dik düşüş + `taper_len` + `bridge_len`, `arm_ov=0`) siyah pileli eteğin geri geldiğini doğruladı.
  - **Ara regresyon bulgusu (`medium__skirt-tucked`):** `taper_len` + `bridge_len` uzatması tüm profillere uygulandığında `medium__skirt-tucked` (`runs/pilot-20261112T134159Z-0f5fc876`, `target` özdeşken yalnızca `ly=76..79`'daki 22 latent hücresi farkıyla) bej culotte şorta döndü; buna karşılık `taper_len` ve `bridge_len` de yalnızca `narrow_silhouette` (`hip_span < round(height * 0.195)`) dalına alındı.
- Uygulanan nihai değişiklikler:
  - [`ai-worker/app/local_skirt_inputs.py`](file:///c:/Users/Hulusi/Desktop/aktif-projeler/TryFit2/ai-worker/app/local_skirt_inputs.py): `_aline_skirt_envelope` içinde dar kalça silüetlerinde (`hip_span < round(height * 0.195)`) ön-kol içi genişleme / bilek sıkışması ve etek ucu aşırı kanat açılımı yerine `base_flare` ile kalça genişliğini koruyan sürekli düşüş (`hip..hem`) + `hem` altında yalnızca dar silüete özgü `taper_len` (~`0.01*H`) ve iç uyluk `bridge_len` (~`0.03*H`) eklendi; `medium` ve `fuller` için önceki A-line geometrisi aynen korundu.
  - [`ai-worker/tests/test_local_skirt.py`](file:///c:/Users/Hulusi/Desktop/aktif-projeler/TryFit2/ai-worker/tests/test_local_skirt.py): Mevcut test güvenceleri gevşetilmeden dar silüet süreklilik, kol kaçınma ve ikili arka plan regresyon testi (`test_narrow_silhouette_avoids_hem_wing_flare_and_bridges_thigh_gap`) eklendi.
- 6-vaka canlı GPU doğrulaması (`37°C -> 52°C`, tümü görsel `read_file` ile doğrulandı, `mode="untiled"`, `peak_allocated_gib=3.574`, `peak_reserved_gib=4.676`; `slender` koşuları nihai `narrow_silhouette` dalı üzerinde `if narrow_silhouette:` ayrımından hemen önce, `medium`/`fuller` koşuları nihai kod üzerinde çalıştırıldı):
  - `slender__skirt-tucked` (`runs/pilot-20261112T133804Z-fba3d380`, `42.84s`): **BAŞARILI** (net siyah pileli mini etek + gümüş C-toka, eski `c910139d`'ye göre daha doğal A-line hat).
  - `slender__skirt-untucked` (`runs/pilot-20261112T133952Z-ff710c72`, `43.97s`): **BAŞARILI** (koyu antrasit/siyah pileli mini etek, şort yok; diğer `untucked` profillerdeki gibi maske alt kenarında arka plan parlaklık farkı kutu izi görülür kalıyor).
  - `medium__skirt-tucked` (`runs/pilot-20261112T134930Z-8ae211d3`, `43.86s`): **BAŞARILI** (siyah pileli mini etek + gümüş toka; regresyon giderildi).
  - `medium__skirt-untucked` (`runs/pilot-20261112T135120Z-b9ae172a`, `43.61s`): **BAŞARILI**.
  - `fuller__skirt-tucked` (`runs/pilot-20261112T135259Z-385ce953`, `43.83s`): **BAŞARILI**.
  - `fuller__skirt-untucked` (`runs/pilot-20261112T135437Z-b961a7d1`, `44.20s`): **BAŞARILI**.

Sonraki mantıklı adım: `K14` (`slender__skirt-untucked` renk kayması) ve tüm profillerdeki ham `02-skirt-raw.png` arka plan parlaklık basamağı / ince bacak kenar çizgisi kalite iyileştirmesi için ayrı tek-değişkenli çalışma yürütmek.
- Testler ve CPU maske kontrolleri:
  - `.\.venv\Scripts\python.exe -m unittest discover -s ai-worker\tests -v`: `122` test çalıştı (`120` geçti, `2` GPU/`CatVTON` ortamı atlandı).
  - `.\.venv-catvton\Scripts\python.exe -m unittest ai-worker.tests.test_catvton -v`: `24` test (`23` geçti, `1` explicit GPU testi atlandı).
  - Tüm 6 profilde CPU maske doğrulaması: `partial_bg=0`, `arm_ov=0`, `min_arm_gap_on_bg=3px`. (Not: `unittest ai-worker.tests.test_local_skirt` tek başına çağrıldığında mevcut `test_lower_records_vae_decode_and_failure_telemetry_without_gpu` testi Windows `torch` çift-import docstring hatası vermekte, `unittest discover` altında temiz geçmektedir.)

## K17 Arka Plan Parlaklık Basamağı ve Bacak Kenarı İzi (Aşama 1–3, `medium__skirt-untucked`) — 12 Kasım 2026

- **Amaç ve kapsam**: CatVTON çıktısında özellikle `untucked` vakalarda etek altında görülen stüdyo arka plan parlaklık basamağını ve dış bacak konturundaki ince parlak kenar izini; ham inference, CatVTON girdileri, hard/soft/preserve maskeleri ve Adaptive VAE Decode davranışına dokunmadan yalnızca raw sonrasında (`repaint_result` öncesinde) azaltmak.
- **Aşama 1 — Algoritma (`ai-worker/app/local_skirt.py`)**:
  - `restore_raw_background` (ve yardımcı fonksiyonlar `_non_letterbox_mask`, `_estimate_exterior_background`, `_connected_from_seeds`) eklendi ve `lower()` içinde ham `02-skirt-raw.png` diske yazıldıktan sonra `repaint_result` çağrısından hemen önce uygulandı.
  - Dış stüdyo arka planı referansı edit maskesi dışından (`~edit_mask`) letterbox şeritleri hariç tutularak satır bazlı kayan medyan (`t_row`, `r_row`) ile tahmin edilir; mutlak parlaklık eşiği kullanılmaz.
  - Ten (`R-B >= 14`, kroma ve `r_row` mavi kanalı farkı), kumaş/toka çekirdek bileşenleri ve emin olunamayan pikseller korunur; yalnızca dış arka planla 8-bağlantılı güvenli arka plan pikselleri ile `<= 2.5 px` kalınlığındaki dar nötr parlak kenar izi `cat-target.png` / satır bazlı arka plan tonuna geri yüklenir.
- **Aşama 2 — CPU regresyon testleri (`ai-worker/tests/test_local_skirt.py`)**:
  - GPU gerektirmeyen 3 test eklendi (`untucked` stüdyo arka plan basamağı, bacak dış kenar parlak izi, siyah/açık renk etek + toka koruması, ten koruması, hedefteki tayt piksellerinin arka plana dönmemesi, belirsiz piksellerin korunması, raw çıktının değişmeyip `repaint_result`'a düzeltilmiş raw iletilmesi).
- **Aşama 3 — Tek vaka GPU A/B (`medium__skirt-untucked`)**:
  - Koşu: `runs/pilot-20261112T141701Z-c0fa9e91` (`runs/pilot-20261112T135120Z-b9ae172a` baz alınarak).
  - Girdiler, maskeler (`cat-hard-mask.png`, `cat-soft-mask.png`, `cat-preserve.png`) ve ham çıktı (`02-skirt-raw.png`) SHA-256 düzeyinde birebir aynı kaldı (`L1=0.0000`); `02-skirt-repaint.png` üzerinde soft mask (`>0`) dışında tek bir piksel bile değişmedi (`0 px`).
  - Etek altı stüdyo arka plan basamağı (`y=615..669`) ortalama `+7.95` luma (maks `+11.00`) seviyesinden ortalama `+0.52` luma (maks `+1.70`) seviyesine düştü.
  - Bacak bölgesinde (`y=680..910`) `P_lum > 212` parlak piksel sayısı `2418` → `302` (`result.png` bacak bandında `1895` → `450`) olarak azaldı; siyah etek pikselleri (`<80 RGB`, `42440 px`) `0.0000` L1 farkla, çıplak ten (`22379 px`) `0.0170` ortalama L1 farkla korundu.
  - `catvton_vae_decode`: `mode=untiled`, `oom_fallback=false`, `peak_allocated_gib=3.574`, `lower_elapsed_seconds=44.17`.
- **Kalan 5-Vaka GPU Kabul Doğrulaması (tümü `mode=untiled`, `oom_fallback=false`, `peak_allocated_gib=3.574`; `01-top.png`, `cat-target.png`, `cat-hard-mask.png`, `cat-soft-mask.png`, `cat-preserve.png` ve `02-skirt-raw.png` SHA-256 birebir aynı, `raw L1=0.0000`; `02-skirt-repaint.png` üzerinde soft mask dışı değişiklik `0 px`, siyah etek `<80 RGB` L1 `0.0000`, ayak/bilek `y>=920` değişiklik `0 px`)**:
  - `slender__skirt-tucked` (`fba3d380 -> eb01112b`, `45.67s`): **KABUL** — Etek ucu arka plan adımı `+3.69 -> -0.14` (maks `+9.59 -> +2.41`), bacak `P_lum>212` `676 -> 11` (`result` bacak bandı `644 -> 239`), çıplak ten L1 `0.0090`; siyah pileli etek, C-toka ve K16 düzeltmesi (şort regresyonu yok) korundu.
  - `slender__skirt-untucked` (`ff710c72 -> 9f533974`, `44.70s`): **KABUL** — Etek altı stüdyo kutusu farkı `+7.41 -> +0.01` (maks `+10.74 -> +1.41`), bacak `P_lum>212` `1418 -> 45` (`result` `1310 -> 263`), çıplak ten L1 `0.0125`; K16 A-line silüeti korundu (`K14` kaynaklı önceden var olan etek içi renk/doku karakteri `02-skirt-raw.png` ile özdeş bırakıldı).
  - `medium__skirt-tucked` (`8ae211d3 -> 79a0c8d7`, `44.77s`): **KABUL** — Arka plan adımı `+7.55 -> -0.06` (maks `+15.39 -> +2.00`), bacak `P_lum>212` `1553 -> 131` (`result` `1247 -> 316`), çıplak ten L1 `0.0169`; pileler, C-toka, üst giysi ve eller korundu.
  - `fuller__skirt-tucked` (`385ce953 -> 420ab6ee`, `44.51s`): **KABUL** — Köşe üçgenleri ve bacak kenar izi temizlendi (maks adım `+7.30 -> +1.55`, bacak `P_lum>212` `758 -> 44`, `result` `767 -> 355`), çıplak ten L1 `0.0116`; silüet, pileler, C-toka ve parmak/el ayrımı korundu.
  - `fuller__skirt-untucked` (`b961a7d1 -> 708a38da`, `44.55s`): **KABUL** — Etek yan/alt arka plan kutusu `+7.07 -> -0.06` (maks `+12.31 -> +1.98`), bacak `P_lum>212` `1197 -> 134` (`result` `1091 -> 396`), çıplak ten L1 `0.0309`; etek, pileler, tişört sınırı ve eller korundu.
- **Testler ve K17 Durumu**:
  - `.\.venv\Scripts\python.exe -m unittest discover -s ai-worker\tests -v`: `125` test çalıştı (`123` geçti, `2` GPU/`CatVTON` ortamı atlandı).
  - `.\.venv-catvton\Scripts\python.exe -m unittest ai-worker.tests.test_catvton ai-worker.tests.test_catvton_skirt ai-worker.tests.test_local_skirt -v`: `40` test (`39` geçti, `1` explicit GPU testi atlandı).
  - **K17 tamamlandı ve commit edildi** (`6/6` synthetic 2-flow vakasında doğrulandı; commit: `2102129`, K16 commit'i `dd9817d` üzerinde).
- **Sonraki mantıklı adım (dönem kaydı)**:
  - K17 değişikliklerinin commit edilmesinin (`2102129`) ardından `K14` (`slender__skirt-untucked` doku/renk kayması) ayrı görev olarak incelendi ve aşağıda belgelendi.

## K14 Kontrollü Maske Çapası Deneyi ve Geri Alma — 12 Kasım 2026

- **Başlangıç durumu ve teşhis (`9f533974`, K17 commit `2102129` sonrası)**:
  - `K14` (`slender + tshirt + tuckTop=false`) senaryosunda siyah eteğin sıcak kahverengi/bronza kaymasının K17 `restore_raw_background` adımından etkilenmediği (`ff710c72` ile `9f533974` arasında `02-skirt-raw.png` SHA-256 özdeş `720d9cc1b033`, etek içi `|raw - repaint| = 0.0000`) ve doğrudan CatVTON `02-skirt-raw.png` üretiminde oluştuğu doğrulandı. Baseline `9f533974` çekirdek etek bölgesi (`cat_y=480..565, x=315..450`): `RGB=[33.85, 30.33, 30.60]`, `R-B=+3.25`, `Lab=(11.78, +1.77, +0.45)`, K16 siyah pileli A-line etek silüeti korunuyor.
- **Kontrollü deneme (`local_skirt_inputs.py`, `test_local_skirt.py`)**:
  - Yalnızca `narrow_silhouette and not tuck_top` dalında `waist` çapası merkez gövde sütunlarının `top` alt sınırı medyanına çekildi (`377 -> 354`); buna bağlı olarak `hip` (`489 -> 466`) ve `hem` (`558 -> 535`) değerleri de `23 px` yukarı kaydı.
  - CPU doğrulamaları geçti: `.venv` `127` test (`2` GPU/CatVTON ortamı atlandı), `.venv-catvton` `42` test (`1` GPU smoke testi atlandı). Kayıtlı `01-top.png` parse çıktılarında yalnızca `slender__skirt-untucked` maskesi değişti (`hard_diff_px=2526`, toplam edit piksel `71487 -> 69161`: üst basende `+100 px`, alt uyluk `y=635..675` bandında `-2426 px`); diğer beş profilin (`slender_tucked`, `medium_tucked`, `medium_untucked`, `fuller_tucked`, `fuller_untucked`) maskelerinde piksel farkı `0` kaldı.
- **Tek GPU A/B koşusu (`slender__skirt-untucked`, `runs/pilot-20261112T153957Z-749bb9eb`) — BAŞARISIZ**:
  - Siyah pileli A-line etek yerine açık kahverengi/bej desenli kısa şort üretildi (`02-skirt-raw.png` ve `02-skirt-repaint.png` çekirdek `480..565, 315..450`: `RGB=[170.42, 134.17, 112.97]`, `R-B=+57.44`, `Lab=(58.24, +11.06, +16.92)` vs baseline `9f533974`: `RGB=[33.85, 30.33, 30.60]`, `R-B=+3.25`, `Lab=(11.78, +1.77, +0.45)`).
  - Kök neden: `waist` değişikliğinin `hip` ve `hem` değerlerini de `23 px` yukarı çekmesi alt maske geometrisini daraltıp kısalttığı (`cat_y=635..675` bandından `2426 px` eksilmesi) için CatVTON UNet üretimini bozup kısa şort moduna itti.
- **Geri alma, testler ve kapanış durumu**:
  - K14 denemesinde `ai-worker/app/local_skirt_inputs.py` ve `ai-worker/tests/test_local_skirt.py` dosyalarına eklenen değişiklikler tamamen geri alındı; K16/K17 kabul edilmiş davranışları ve `9f533974` baseline'ı dahil tüm `6` profilin maske geometrisi (`hard_diff_px=0`, `soft_diff_px=0`) korundu.
  - Geri alma sonrası testler hatasız tamamlandı: `.venv` `125` test (`123` geçti, `2` atlandı), `.venv-catvton` `40` test (`39` geçti, `1` atlandı).
  - K14 denemesinin geri alınması ve belge kaydı sonrasında çalışma `e60a7ae` commit'i ile sabitlendi (`dd9817d` K16 ve `2102129` K17 baseline'ı korundu). K14'ün mevcut hafif sıcak renk kayması açık fakat ertelenmiş bilinen konu olarak bırakıldı; şu an yeni model deneyi yürütülmüyor.

## Gerçek Pilot Pantolon Kaynağı Kabulü ve Pilot Bekleme Durumu — 12 Kasım 2026

- **Korunan model/pipeline baseline'ı**:
  - `K16` (`dd9817d`) ve `K17` (`2102129`) çözülmüş ve commit edilmiş baseline (`9f533974`) olarak korunmaktadır; `K14` (`e60a7ae`) açık fakat ertelenmiş, `K15` ise açık kalmaya devam etmektedir.
- **Kabul edilen gerçek pilot pantolon kaynağı (`pilot-trousers`)**:
  - `wide-trousers` üzerindeki AI-üretim etiketi ve kullanıcı eki pijama altı adayları elendikten sonra, gerçek mankenli ve AI etiketsiz `Mavi New York Kahverengi Gabardin Pantolon 101441-91340` (`1101117577`, Galeri 3) indirildi (Git dışı `data/pilot/trousers-product.jpg`, `621×931` RGB, SHA-256 `f8190f2c684d039f1f6a2a28274c23d6f70e95c4994ffdbc66ea533d4c4ec07c`; kaynak metadata'sı `data/pilot/sources.json`).
  - [`evaluation/annotations/pilot-trousers.sam2.json`](../evaluation/annotations/pilot-trousers.sam2.json) tanımı (yalnızca ürün ID, SHA-256 ve normalize nokta koordinatları içerir; kişisel/hassas veri içermez) ve `runs/source-extraction-pilot-trousers-refined/` (`mask_sha256: 30ac381008f89e014b01d299d8afc22d4f53266c978abcc2aa4a4b8294b162d6`) üretildi; `pilot_runner.verify_pilot_extractions` doğrulamasından geçerek kabul edilmiş pantolon kaynağı olarak kaydedildi.
- **İnsan fotoğrafı veri kaynakları incelemesi ve gerçek pilotun bekleme nedeni**:
  - Üç farklı vücut yapısını (`slender`, `medium`, `fuller`) temsil eden yetişkin kadın tam boy fotoğrafları için incelenen kamuya açık ve stok veri setlerinde (VITON-HD, Dress Code, DeepFashion/MultiModal, FIT, Fashionpedia, Open Images, Wikimedia Commons, SHHQ, ModaNet, CIHP/LIP/ATR, BodyM, Unsplash, Pexels vb.) TryFitNext için gereken ticari kullanım ve doğrulanabilir model rızası koşulları birlikte doğrulanamadı.
  - Bu nedenle `3` gönüllü yetişkin kadın katılımcı fotoğrafı (`data/pilot/target-{1,2,3}.jpg`) ve doğrulanabilir yazılı rıza kayıtları (`adult_confirmed`, `consent_confirmed`, `consent_record_id`, `retention_until`) temin edilinceye kadar gerçek `3×3` pilot **beklemeye alındı**.
  - Mevcut `--synthetic-tech` / tekil sentetik pilot koşuları yalnızca teknik prova ve regresyon kontrolüdür (`effective_subject_diversity: 1`, `generalization_evidence: false`); **gerçek kullanıcı kalite kanıtı değildir**.
- **Sonraki mantıklı adım**:
  - Gönüllü katılımcı fotoğrafları ve rıza kayıtları beklenirken K16/K17 baseline'ını koruyarak katılımcı verisi gerektirmeyen teknik veya mimari işlerle devam etmek; fotoğraflar ve rızalar sağlandığında Git dışı gerçek manifest üzerinden `validate -> preflight -> run` adımlarıyla gerçek pilotu yeniden başlatmak.

## Bağımsız Çift Değerlendirici Pilot Özet Aracı (pilot_evaluator.py) — 12 Kasım 2026

- **Amaç ve tasarım**:
  - Gerçek 3×3 pilot (ve sentetik 2-akış teknik provaları) için `pilot_runner.py` tarafından üretilen `review-template.csv` çıktısını iki bağımsız değerlendirici üzerinden okuyan, sentezleyen ve uyuşmazlıkları raporlayan bağımsız bir değerlendirme aracı oluşturuldu ([`ai-worker/app/pilot_evaluator.py`](../ai-worker/app/pilot_evaluator.py)).
  - Mevcut `experiment.py evaluate` (10 ürünlük benchmark aracı) ve `pilot_runner.py` çalışma anı koduna dokunulmadı; sözleşmeler izole tutuldu.
- **Uygulanan temel kurallar**:
  1. **Değerlendirici uyuşmazlıkları**: İki değerlendiricinin ham puanları (`evaluator_1`, `evaluator_2`) ayrı ayrı korunur. Mutlak puan farkı `>= 2` olan metrikler `score_discrepancies` altında listelenir ve `human_adjudication_required: true` bayrağı tetiklenir. Otomatik vaka kararı muhafazakar olarak `min(r1, r2)` puanına dayanır ancak bu geçici bir otomatik hesaplamadır; insan uzlaşması yerine geçmez. Herhangi bir değerlendiricinin `critical_failure=yes` veya `untargeted_changes=yes` işaretlemesi doğrudan veto uygular (`provisional = failed`).
  2. **Dinamik vaka türetimi**: 9 veya 12 vaka sabit kodlanmaz; beklenen vakalar `pilot-summary.json` ve `manifest.json` üzerinden dinamik türetilir. Üretilmeyen vakalar `not_generated` / `parse_blocked` olarak raporlanır; fazla veya tekrarlanan vaka kimlikleri reddedilir. `top_only` akışlarında ek 3 metrik için `N/A` kabul edilir; iki parçalı akışlarda (`trousers`, `skirt`) ek metriklerde `N/A` reddedilir (`0..4` puan zorunludur).
  3. **Kalite kapısı ayrımı**: Çıktı `pilot_acceptance` altında raporlanır (`provisionally_acceptable`, `pending_human_adjudication`, `pending` veya `failed`). `general_quality_gate` daima `not_established` kalır ve `generalization_evidence: false` korunur; sınırlı 3 katılımcılı pilotun genel ürün kalitesini kanıtlamadığı açıkça belirtilir.
- **Birim testler (`ai-worker/tests/test_pilot_evaluator.py`)**:
  - 15 birim test (`test_two_reviewers_full_pass`, `test_score_discrepancy_detected`, `test_veto_by_single_reviewer_critical_failure`, `test_veto_by_single_reviewer_untargeted_changes`, `test_top_only_allows_na_for_extra_metrics`, `test_two_stage_rejects_na_for_extra_metrics`, `test_dynamic_case_count_derivation`, `test_unexecuted_manifest_case_reported_as_not_generated`, `test_unexpected_case_id_rejected`, `test_single_reviewer_rejected`, `test_duplicate_review_by_same_reviewer_rejected`, `test_identical_reviewer_names_rejected`, `test_mismatched_target_or_flow_id_rejected`, `test_parse_blocked_and_failed_cases_never_pass_even_with_perfect_scores`, `test_cli_main_execution`) CPU üzerinde %100 geçti (`15/15 OK`, 0.075s).
- **Mevcut testlerin kapanışı ve doğrulanmış durum**:
  - `ai-worker/tests/test_pilot.py`: `test_template_has_no_real_files_or_consent_and_is_rejected_unfilled` testi, `data/pilot/trousers-product.jpg` gibi bilerek indirilmiş yerel ürün dosyalarının varlığından bağımsız hale getirildi; şablonun boş ürün alanları (`image_sha256`, `product_url`, `source_image_url`, `source_notes`) ve `validate_pilot_manifest` ValueError fırlatma davranışı korundu. `test_pilot.py` içindeki tüm `33/33` test hatasız geçti.
  - `.venv` test paketi (`.\.venv\Scripts\python.exe -m unittest discover -s ai-worker\tests`): `140` test çalıştı; `138` test geçti, `2` test atlandı (GPU entegrasyonu ve CatVTON ortamı gerektiren testler), `0` hata / `0` başarısızlık (`OK (skipped=2)`).
  - `.venv-catvton` test paketi (`.\.venv-catvton\Scripts\python.exe -m unittest ai-worker.tests.test_catvton ai-worker.tests.test_catvton_skirt ai-worker.tests.test_local_skirt`): `40` test çalıştı; `39` test geçti, `1` test atlandı (açık GPU testi), `0` hata / `0` başarısızlık (`OK (skipped=1)`).
  - Tüm test paketlerinde başarısız test kalmadı.
- **Sonraki mantıklı adım**:
  - Gönüllü katılımcı fotoğrafları ve rıza kayıtları temin edildiğinde gerçek pilot koşusunu çalıştırmak ve iki bağımsız değerlendiricinin dolduracağı CSV dosyalarını `pilot_evaluator.py` ile sentezlemek.

## Üç Bağımsız Sentetik Avatar ile Multi-Subject Teknik Pilot — 13 Kasım 2026

- **Amaç ve Sınırlar**:
  - Gerçek insan fotoğrafları ve rıza kayıtları temin edilinceye kadar teknik geliştirmeyi sürdürebilmek amacıyla; tekil bir temel görselden türetilmemiş, sıfırdan bağımsız üretilmiş 3 farklı sentetik yetişkin kadın avatarı (`slender`, `medium`, `fuller`) hazırlandı.
  - Bu teknik pilot, **kesinlikle gerçek insan genellenebilirliği veya ürün kalite kapısı kanıtı değildir** (`generalization_evidence: false`, `manifest_kind: "synthetic_multisubject_pilot"`, `effective_subject_diversity: 3`).
- **Üretilen Bağımsız Avatarlar ve Ön Doğrulamalar**:
  - `data/avatar-profiles/avatar-slender-indep.png` (848×1264 RGB, SHA-256: `9e9da196a01af258cdac044cc04351dcde0fd2d1cad2b7d1a9d3421fa8b82637`)
  - `data/avatar-profiles/avatar-medium-indep.png` (848×1264 RGB, SHA-256: `235a8275be12dbcf8215ddc10a6528a7303ab46fdd2f8b7647a942d8423c334e`)
  - `data/avatar-profiles/avatar-fuller-indep.png` (848×1264 RGB, SHA-256: `17d83cec147c5af1669fe3ef7927c96548084626cf3941a4d57748e2b21dc9e6`)
  - Her 3 avatar da sade açık gri tişört ve orta gri bilek boyu tayt ile bağımsız promptlarla sıfırdan üretildi. `fashn-human-parser` ile CPU preflight'ında üst (`label 3`), alt (`label 6`) ve ayak (`label 15`) etiketleri eksiksiz doğrulandı (`passed_skirt_requirements: true`, `passed_trousers_requirements: true`).
  - `skirt_inputs` CPU üzerinde her 3 avatar için test edildi; hem `tuck_top=true` (bel kesimiyle) hem de `tuck_top=false` durumunda hatasız etek maskesi poligonu (10 nokta) ve handoff üretildi.
- **Üretim Kaydı ve Manifest**:
  - [`evaluation/annotations/avatar-profiles-independent.generation.json`](../evaluation/annotations/avatar-profiles-independent.generation.json): Promptlar, araç kimliği, piksel boyutları ve SHA-256 hash'leri kaydedildi.
  - [`evaluation/manifests/pilot-synthetic-3subject.json`](../evaluation/manifests/pilot-synthetic-3subject.json): 3 hedef × 3 akış = 9 vaka (`slender`, `medium`, `fuller` × `top`, `skirt-tucked`, `skirt-untucked`). `same_base_identity: false`, `effective_subject_diversity: 3`, `derived_from_baseline: null`.
- **Doğrulayıcı ve Koşucu İzolasyonu (`pilot_runner.py`, `pilot_evaluator.py`)**:
  - `pilot_runner.py`: `validate_synthetic_pilot_manifest` fonksiyonu `synthetic_multisubject_pilot` türünü destekleyecek şekilde minimal olarak genişletildi. Bağımsız avatar hedeflerinde `target_origin: synthetic_independent_avatar`, `derived_from_base_image: null` ve diskte mevcut `generation_record` dosyası şart koşuldu. Hedef SHA-256 kopyalamaları, sahte rıza alanları, geçersiz çeşitlilik/kimlik değerleri engellendi. Gerçek insan pilotu doğrulayıcısı `validate_pilot_manifest` yeni manifesti reddedecek şekilde korundu. Eski `synthetic_technical_pilot` doğrulaması aynen muhafaza edildi.
  - `pilot_evaluator.py`: `is_synthetic` kontrolüne `synthetic_multisubject_pilot` eklendi; `derive_expected_cases` fonksiyonunun 9 vakayı dinamik olarak türetebildiği doğrulandı.
- **Birim Testler ve Doğrulama**:
  - `ai-worker/tests/test_pilot.py`: 3 yeni test eklendi (`test_repo_multisubject_synthetic_manifest_contract_and_live_extractions`, `test_multisubject_synthetic_manifest_guards_and_rejections`, `test_end_to_end_9_case_multisubject_synthetic_mock_run_verifies_every_avatar_and_flow`). Test sayısı 33'ten 36'ya çıktı; tümü geçti (`36/36 OK`, 11.75s).
  - `ai-worker/tests/test_pilot_evaluator.py`: 15 testin tamamı geçti (`15/15 OK`, 0.05s).
  - `.venv` discover (`.\.venv\Scripts\python.exe -m unittest discover -s ai-worker\tests -v`): 143 testin 141'i geçti, 2'si atlandı (`141 passed, 2 skipped, 0 failed`).
  - `.venv-catvton` test paketi: 40 testin 39'u geçti, 1'i atlandı (`39 passed, 1 skipped, 0 failed`).
- **İlk 9-Vakalı GPU Koşusu (`runs/pilot-20261112T223705Z-20783618`) — 13 Kasım 2026**:
  - Preflight doğrulaması (`runs/pilot-20261112T223633Z-83d71826`): Üç bağımsız avatar da CPU parser kontrolünü hatasız geçti (`passed_skirt_requirements: true`, `passed_trousers_requirements: true`, `missing_for_skirt_envelope: []`).
  - 9 vakanın tamamı NVIDIA GeForce RTX 4060 Ti üzerinde başarıyla tamamlandı (`status: completed`, `9/9 completed`). Sıfır hata, sıfır parse engeli.
  - VAE decode: 6 etek vakasının tamamında `mode: untiled` olarak gerçekleşti (OOM fallback gerekmedi).
  - GPU VRAM: En yüksek ayrılan bellek `2.167 - 3.574 GiB` (reserved: `4.664 - 5.016 GiB`).
  - Süreler: Tek parça tişört (`top_only`) vakaları ortalama `~39.9s`; iki aşamalı etek kombinleri toplam `~86.7s - 89.0s` (FASHN Phase 1: `~40.3 - 41.8s`, CatVTON Phase 2: `~45.9 - 47.6s`).
  - Çıktılar: 9 vakanın tümünde `result.png` ve `comparison.jpg` üretildi; `pilot-summary.json` ve `review-template.csv` eksiksiz oluşturuldu.
- **Henüz Tamamlanmayanlar / Sınırlar**:
  - Çıktılar üzerinde henüz çift değerlendirici görsel kalite incelemesi yapılmadı; önceden tahminle kalite puanı atanmadı.
  - Bu teknik koşu sentetik bir prova olup kesinlikle gerçek insan genellenebilirliği veya ürün kalite kapısı kanıtı değildir (`generalization_evidence: false`).
  - Gerçek 3×3 insan pilotu izinli fotoğraflar temin edilene kadar beklemede kalmaya devam etmektedir.
  - Sonraki mantıklı adım: İki değerlendiricinin `review-template.csv` çıktısını bağımsız olarak puanlaması ve sonuçların `pilot_evaluator.py` ile sentezlenmesi.

## Kalite Kabul Kuralı Güncellemesi (Kaynak Ürün Kimliği ve Karakteristik Detaylar) — 13 Kasım 2026

- **Belgelenen Karar (D15)**:
  - Sanal deneme çıktısının yalnızca kıyafet kategorisi ve genel rengi doğru olduğu için başarılı sayılamayacağı; kaynak kıyafette fiilen bulunan karakteristik özelliklerin (renk ve desen, kesim ve siluet, kemer/toka gibi aksesuar detayları, pileler ve kumaş dokusu, özgün tasarım özellikleri) korunmasının zorunlu olduğu kalite kabul kararı olarak [decisions.md](decisions.md) (D15) ve [evaluation-protocol.md](evaluation-protocol.md) içine işlendi.
  - Kaynak üründe fiilen bulunmayan detayların zorunlu tutulmayacağı, kararın geçmiş GPU pilot sonuçlarını geriye dönük olarak otomatik değiştirmediği ve mevcut sonuçların yeni kriterle yeniden değerlendirilebileceği belgelendi.
- **Sonraki Mantıklı Adım**:
  - Gemini ve Antigravity tarafından yapılan iki ayrı AI görsel değerlendirmesinin karşılaştırması tamamlanmış olup, bu incelemeler kesinlikle bir insan uzman değerlendirmesi değildir. Nihai karar ve olası pipeline değişiklikleri öncesinde insan uzman doğrulaması şarttır.

## D15 Kararı Sonrası Sentetik Pilot Kalite Yeniden Değerlendirmesi — 13 Kasım 2026

- **Değerlendirilen Koşu**:
  - `runs/pilot-20261112T223705Z-20783618/` (3 bağımsız avatar × 3 akış = 9 vaka).
- **Sonuç Dağılımı**:
  - **4 PASS**, **5 FAIL**, **0 REVIEW**.
- **Akış Bazında Değerlendirme**:
  - **Tişört (`top_only`): 3/3 PASS.**
    - `slender__top`, `medium__top` ve `fuller__top` vakalarının tamamı geçti. Siyah renk (`RGB: [26-29, 26-28, 31-34]`), bisiklet yaka ve basic kesim her üç vücut tipine de başarıyla oturdu; uzuv ve hedef anatomisi tam korundu. D15 Detay Yokluğu Kuralı uyarınca kaynakta bulunmayan aksesuar aranmadı.
  - **Tucked Etek (`top_plus_skirt`, `tuck_top=true`): 0/3 PASS.**
    - `slender__skirt-tucked`, `medium__skirt-tucked` ve `fuller__skirt-tucked` vakalarının üçü de kaldı. Kaynak etekteki kalın kemer tasarımı ve toka detayları korunamadı (slender ve medium'da toka 45-47 piksellik zayıf bir kalıntıya indirgendi, fuller'da kemer/toka 0 piksele inerek tamamen silindi). Pile derinliği ve dikey kat izleri difüzyon sonrası sönümlendi (`garment_identity: 2`, `waist_belt_transition: 1-2`).
  - **Untucked Etek (`top_plus_skirt`, `tuck_top=false`): 1/3 PASS.**
    - `medium__skirt-untucked` geçti (koyu nötr siyah/antrasit renk `RGB: [37, 36, 40]`, 9 vaka içindeki en yüksek pile netliği `Sobel_x: 15.00`).
    - `slender__skirt-untucked` kaldı (belirgin sıcak kahverengi/bronz renk sapması `RGB: [56, 38, 33]`, siyah ürün kimliği kaybı nedeniyle `critical_failure: yes`).
    - `fuller__skirt-untucked` kaldı (dolgun basende kumaşın gerilmesiyle derin pileler neredeyse tamamen açılarak düz kumaşa dönüştü, `Sobel_x: 7.35`, `fabric: 2`).
- **Değerlendirme Sınırları ve İnsan Doğrulaması Şartı**:
  - Bu değerlendirme Gemini ve Antigravity tarafından yapılan iki ayrı AI görsel incelemesine ve doğrudan sayısal piksel kanıtlarına dayanmaktadır; **kesinlikle bir insan uzman değerlendirmesi değildir**.
  - Bu sonuçlar sentetik teknik pilot bulgularıdır; **kesinlikle gerçek insanlarda genellenebilirlik veya ürün kalite kapısı kanıtı değildir** (`generalization_evidence: false`).
- **Sonraki Mantıklı Adım**:
  - İnsan uzman değerlendiricinin sentetik pilot çıktılarını doğrulaması. **Bu insan doğrulaması tamamlanmadan önce pipeline, maske veya kod değişikliği yapılmayacaktır.**

## D15 Bağımsız İnsan (Kullanıcı) Değerlendirmesi — 13 Kasım 2026

- **Değerlendirilen Koşu ve Paket**:
  - `runs/pilot-20261112T223705Z-20783618/` (3 bağımsız sentetik avatar × 3 akış = 9 vaka).
  - `evaluation/human-review/d15-synthetic-pilot/` altında kör/anonimleştirilmiş (`H01`–`H09`) paket üzerinden bağımsız kullanıcı tarafından gerçekleştirilmiştir.
- **Değerlendirici Niteliği ve Kapsam**:
  - Bu değerlendirme bir **bağımsız son kullanıcı değerlendirmesidir**; kesinlikle profesyonel bir tekstil/hazır giyim uzmanı değerlendirmesi değildir.
  - Çalışma sentetik teknik pilot avatarları üzerinde yapılmıştır; **kesinlikle gerçek insanlarda genellenebilirlik veya ürün kalite kapısı kanıtı değildir** (`generalization_evidence: false`).
- **Nihai İnsan Değerlendirme Sonuçları**:
  - **4 PASS**, **5 FAIL**, **0 REVIEW**.
  - Vaka Bazında Kararlar ve Gözlemler:
    - `H01` (`medium__skirt-tucked`): **FAIL** — `fabric: 2`; pile derinliği ve kumaş dokusu yeterince korunmamış.
    - `H02` (`medium__top`): **PASS** — Üst giyim transferi, renk ve kesim başarılı.
    - `H03` (`medium__skirt-untucked`): **FAIL** — `color_pattern: 2`, `waist_belt_transition: 2`; tişört-etek birleşimi (tişörtün kısmen içeri kaçması) ve kemer/kumaş tonu sorunlu.
    - `H04` (`fuller__skirt-tucked`): **FAIL** — `stage1_preservation` son insan değerlendirmesinde 4 olarak düzeltilmiştir; ancak `garment_identity: 1` ve `waist_belt_transition: 1` (kemer ve tokanın tamamen kaybolması) nedeniyle kalmıştır.
    - `H05` (`fuller__skirt-untucked`): **FAIL** — `cut: 2`; etek boyu kaynak üründen farklı ve tişört altında beyaz sınır/hale izi gözlemlenmiş.
    - `H06` (`slender__skirt-tucked`): **PASS** — `fabric: 4`, `waist_belt_transition: 3`; etek ucunda sınırlı saydamlaşma ve tişörtün kemeri kısmen örtmesi not edilmiş, ancak genel deneme başarılı bulunmuştur.
    - `H07` (`fuller__top`): **PASS** — Üst giyim transferi ve silüet başarılı.
    - `H08` (`slender__top`): **PASS** — Üst giyim transferi ve silüet başarılı.
    - `H09` (`slender__skirt-untucked`): **FAIL** — `garment_identity: 0`, `critical_failure: yes`; kaynak ve sonuç eteklerinin tamamen farklı ürün izlenimi vermesi (ciddi renk sapması).
- **AI Değerlendirmeleri (Gemini & Antigravity) ile Karşılaştırma**:
  - **Toplam Dağılım:** Her iki değerlendirme grubu da genel toplamda **4 PASS / 5 FAIL** sonucuna ulaşmıştır.
  - **Tam Uzlaşma Sağlanan 7 Vaka (İttifak):**
    - `H01` (`medium__skirt-tucked`): 3 değerlendirici de **FAIL**.
    - `H02` (`medium__top`): 3 değerlendirici de **PASS**.
    - `H04` (`fuller__skirt-tucked`): 3 değerlendirici de **FAIL**.
    - `H05` (`fuller__skirt-untucked`): 3 değerlendirici de **FAIL**.
    - `H07` (`fuller__top`): 3 değerlendirici de **PASS**.
    - `H08` (`slender__top`): 3 değerlendirici de **PASS**.
    - `H09` (`slender__skirt-untucked`): 3 değerlendirici de **FAIL**.
  - **Ayrışan 2 Vaka:**
    - `H03` (`medium__skirt-untucked`): **İnsan FAIL**, **AI PASS**. AI değerlendirmeleri eteği izole inceleyip pile netliğine odaklanırken; kullanıcı tişört-etek birleşimindeki asimetrik içeri kaçmayı ve ton farkını kusur olarak değerlendirmiştir.
    - `H06` (`slender__skirt-tucked`): **İnsan PASS**, **AI FAIL**. AI değerlendirmeleri katı D15 kuralıyla kemerin incelmesini ve tokanın küçülmesini doğrudan ihlal sayarken; kullanıcı merkezdeki tokayı görmüş ve dökümlü tişörtün kemeri kısmen örtmesini doğal bir giyim durumu sayarak sonuca geçer not vermiştir.
  - İnsan kararları bağımsız nihai kullanıcı değerlendirmesi olarak korunmuş, AI sonuçlarına göre değiştirilmemiştir.
- **Sonraki Mantıklı Adım**:
  - H03 ve H06 vakalarında ortaya çıkan kullanıcı toleransları (doğal tişört dökümü / kemer örtülmesi ve kombin ton uyumu) doğrultusunda D15 tolerans çerçevesinin netleştirilmesi.
  - İnsan doğrulamasının bulguları ışığında, gerçek insan pilotuna geçmeden önce pipeline ve maske iyileştirme yol haritasının belirlenmesi.
