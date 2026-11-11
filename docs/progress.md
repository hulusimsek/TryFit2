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

Sonraki mantıklı adım: kalan profil/üst seçimlerinde çalışma anı maskesini kontrol etmek ve ayak bileği/kenar geçiş izlerini azaltmak; çalışan kemer akışını korumak.
