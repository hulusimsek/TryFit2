# Mimari

İnceleme tarihi: 11 Kasım 2026. Bağlayıcı proje kuralları [AGENTS.md](../AGENTS.md) içindedir. Bu belge mevcut uygulama ile hedef mimariyi ayrı anlatır; canlı dağıtım veya model kalitesi onayı değildir.

## Amaç ve kapsam

TryFit Next, bu `TryFit2` klasöründe geliştirilen bağımsız, fotogerçekçi 2D sanal kıyafet deneme projesidir. Eski `../TryFit` deposu yalnızca referanstır. 3D manken iş akışı kapsam dışıdır. Hazır sentetik kişi görselleri 2D hedef görüntülerdir; boy/kilodan hesaplanan ölçülü vücutlar değildir.

Mevcut sürüm üç hazır profil ve dört seçilmiş ürünle çalışan yerel araştırma ekranıdır. Otomatik Trendyol bağlantısı işleme, kişisel fotoğraf yükleme, gerçek beden uyumu ve tüketiciye açık uygulama tamamlanmış değildir.

## Mevcut bileşenler

| Bileşen | Sorumluluk ve mevcut uygulama |
| --- | --- |
| `src/TryFit.Domain` | `OutfitSelection`, `TryFitJob` ve geçerli iş durumu geçişleri; başka projeye bağımlılığı yok. |
| `src/TryFit.Application` | Seçim/kategori doğrulaması, en fazla üç aktif iş, üretim akışı ve kesilen işlerin kapatılması. `ICatalog`, `IJobRepository`, `IJobQueue`, `ITryOnEngine` arayüzleri burada. |
| `src/TryFit.Infrastructure` | Manifest kataloğu, JSON iş kayıtları, bellek içi kuyruk ve Python süreç adaptörü. İç katmanların arayüzlerini uygular. |
| `web/TryFit.Local` | .NET 9 HTTP API, DI bağlantıları, tek okuyuculu arka plan servisi ve `wwwroot` altındaki araştırma ekranı. |
| `ai-worker/app` | Python inference ve deney araçları. Yerel iş giriş noktası `local_job.py`; FASHN ve önceden hazırlanmış SAM kaynak maskeleri kullanılır. CatVTON ayrı araştırma yoludur. |
| `evaluation`, `runs`, `dist` | Sırasıyla manifest/annotasyonlar, yerel deney ve iş kayıtları, görsel raporlar. `runs` ve `dist` Git dışında tutulur. |

Proje referansları: `Application → Domain`, `Infrastructure → Application`, `Local → Application + Infrastructure`. API'nin Infrastructure referansı DI bileşimini kurar. İş kuralları Application/Domain içinde kalmalı; Domain dış katmanlara bağımlı olmamalıdır. Mevcut dört proje yeterlidir; gerekçe olmadan yeni katman eklenmez.

## Yerel veri akışı

1. Tarayıcı `/api/catalog` üzerinden üç profil ve dört ürünü alır. Yeni ürün URL'si çözümleme yapılmaz.
2. `POST /api/jobs`, `profileId`, `topId`, `bottomId` alanlarını alır. Application seçimi doğrular; geçersiz seçim 400, kapasite doluysa 429, kabul edilen iş 202 döner.
3. İş JSON olarak `runs/local-jobs/<32-haneli-id>/job.json` içine kaydedilir ve bellek içi kuyruğa alınır. Tek arka plan okuyucusu işleri sırayla yürütür.
4. `PythonTryOnEngine`, aynı makinedeki `.venv` Python'unu `local_job.py --job-dir ...` ile başlatır. On dakikalık süre sınırı vardır; model çevrimdışı önbellekle çalıştırılır.
5. Worker üst parçayı FASHN ile hedef maskesiz üretir. Pantolon alt aşaması FASHN ve referans koruması kullanır. Etekte ayrı CatVTON süreci çalışır; hedef maskesi yeni üst görüntüsünden çalışma anında hazırlanır. Etek ekran sonucu repaint'tir: maskenin düzenlemediği bölgeler hedeften kopyalanır, ham ağ çıktısı ayrıca saklanır. `TuckTop`, üstün etek ucunun içeri alınmasına izin verilen giyim seçimini taşır; yalnız seçili etekte desteklenir.
6. Adaptör `outcome.json` içindeki durumu, `result.png` imzasını ve SHA-256 değerini doğrular. Başarısız üretimde hazır görsel başarı diye döndürülmez.
7. İstemci `/api/jobs/{id}` ile durumu, `/api/jobs/{id}/result` ile tamamlanmış PNG'yi alır. HTTP yanıtı `JobResponse` ile eşlenir; Domain nesnesi doğrudan dönülmez.

Durumlar `queued → running → completed/failed` şeklindedir; aktif işler de kesinti nedeniyle başarısız yapılabilir. Yeniden başlatmada kayıtlar yüklenir, aktif işler başarısız işaretlenir; otomatik devam ettirme yoktur. `completed`, dosya üretildiğini ifade eder; görsel kalite kabulü anlamına gelmez.

## Worker sözleşmesi ve sınırı

Bugünkü sözleşme HTTP servisi değildir: aynı dosya sistemi üzerinde `request.json` girdisi, süreç çıkış kodu, `outcome.json`, `result.png` ve `worker.log` kullanılır. İstek üç seçim kimliğini ve isteğe bağlı `tuckTop` değerini taşır; eski kayıtlarda bu değer false kabul edilir. Etek alt süreçleri hash'li `skirt-handoff.json` ile hazırlanan gerçek görüntü/maske/condition dosyalarını aktarır. Üst FASHN süreci kapandıktan sonra CatVTON süreci başlar. Başarılı outcome durum, motor/yöntem bilgisi ve çıktı hash'ini içerir. İlerleme süreç çıktısındaki metinlerden okunur. Ayrıntılar: [adaptör](../src/TryFit.Infrastructure/PythonTryOnEngine.cs), [worker](../ai-worker/app/local_job.py), [etek iş akışı](../ai-worker/app/local_skirt.py).

Python kodu ayrı klasördedir fakat bugünkü adaptör aynı çalışma alanına, sanal ortama ve yerel modellere bağlıdır. Bağımsız uzak dağıtım tamamlanmış değildir. `/api/health` içindeki `ready` yalnızca Python dosyasının varlığını kontrol eder; GPU/ağırlık sağlığı kanıtı değildir.

## Hedef üretim mimarisi — henüz uygulanmadı

- Frontend ve Chrome eklentisi ayrı istemciler olarak .NET API'ye bağlanacak. Mevcut ekran API ile aynı hostta sunulur; yeni projede Chrome eklentisi yoktur.
- Üretim inference'ı bağımsız dağıtılabilen Python worker üzerinde uzak GPU'da çalışacak. Backend yerel GPU gerektirmeyecek; mevcut yerel adaptör araştırma uygulamasıdır.
- Uzak adaptör `ITryOnEngine` sınırını koruyacak. TODO: taşıma yöntemi, sözleşme sürümü, zaman aşımı/iptal, tekrar deneme ve çıktı aktarımı ihtiyaca göre tanımlanacak; sağlayıcı ve kuyruk ürünü seçilmedi.
- TODO: kullanıcı/iş sahipliği, yetkilendirme, özel görsel depolama ve silme politikası uygulanacak. Yerel uygulamada kimlik doğrulama yok; yalnızca `127.0.0.1:5187` üzerinde dinliyor ve çok kullanıcılı yayın için hazır değil.
- Ücretli servis veya kaynak açık onay olmadan sağlanmaz. Ücretsiz Colab araştırma içindir; sürekli üretim API'si olarak kabul edilmez.

Model kalitesi ve lisans uygunluğu dağıtım kararından ayrıdır. [Bilinen sorunlar](known-issues.md), [kararlar](decisions.md) ve [değerlendirme protokolü](evaluation-protocol.md) birlikte okunmalıdır.
