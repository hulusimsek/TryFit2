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

Sonraki mantıklı adım: Veri temini, açık rıza kaydı doğrulaması ve yeni pantolon ürününün SAM2 kaynak maskesi hazırlığı (Görev 3) için kullanıcı onayı almak; ardından doldurulmuş yerel pilot manifestiyle `pilot_runner.py validate` / `preflight` ve `run` adımlarını çalıştırıp elde edilen `9` (veya opsiyonel kontrolle `12`) çıktıyı bağımsız değerlendiricilerle puanlayarak `36 + 24 = 60` üretimlik ana doğrulamaya geçiş kararını vermek.

