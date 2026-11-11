# TryFit Next

## Çalışan yerel ekran

**[TryFit'i aç](http://127.0.0.1:5187)** → hazır profil + üst + alt seç → **Kombini dene**. Gerçek yerel GPU üretimi yaklaşık 1–2 dakika sürer; sonuç PNG olarak indirilebilir. Sunucu kapalıysa [Start-TryFit.cmd](Start-TryFit.cmd) dosyasını çift tıklayın ve adresi açın.

Bu sınırlı araştırma ekranı .NET 9 API + Python worker ile çalışır. Şimdilik dört seçilmiş ürün ve üç sentetik hazır görünüm vardır; yeni ürün bağlantısı alma ve boy/kilodan ölçülü manken üretimi henüz yoktur. [Kullanım, doğrulama ve sınırlar](docs/local-app.md).

Pileli etek seçildiğinde güncel ekran gerçek FASHN üst + ayrı CatVTON etek üretimini kullanır. **Üstü eteğin içine al** seçeneği varsayılan açıktır; kapatılırsa uzun üst kemeri örtebilir. Bu araştırma yönteminde maske dışı hedef pikselleri korunur; ham ve repaint sonuçları ayrı kaydedilir. Pantolon yolu FASHN olarak sürer.

## .NET mimarisi

[TryFit.sln](TryFit.sln) dört projeden oluşur.

- **Domain** kombin seçimini ve bir işin geçerli durum geçişlerini tanımlar.
- **Application** ürün seçimini doğrular, iş kuyruğunun kapasitesini uygular ve üretim akışını yönetir. Katalog, kayıt, kuyruk ve model için arayüzleri tanımlar.
- **Infrastructure** bu arayüzleri yerel manifestler, JSON iş kayıtları, bellek içi kuyruk ve Python modeliyle uygular.
- **Local** HTTP uçlarını ve statik ekranı sunar. `Program.cs` uygulama arayüzlerini altyapı uygulamalarına bağlar.

Application yalnızca Domain'e, Infrastructure ise Application'a referans verir. HTTP yanıtları ve diskteki iş kayıtları ayrı modellerle eşlenir. Çözümü derlemek için `dotnet build TryFit.sln` çalıştırın.

Bağımsız 2D AI Virtual Try-On araştırması. Ürün hedefi: Trendyol'dan seçilen parçaları birlikte, kullanıcının boy/kilo profiline yaklaşık eşleşen bir manken üzerinde göstermek. Kullanıcının kendi fotoğrafı zorunlu değildir. Colab notebook tek parça aktarımını; `ai-worker/app/outfit.py` yerel iki parçalı ardışık aktarımı test eder.

İlk kombin seçimi `evaluation/manifests/first-outfit.selection.json` dosyasında: 175 cm / 65 kg deneme profili, lacivert kapüşonlu üst (flat-lay) ve siyah/beyaz puantiyeli pijama altı (model). Kullanıcının yüklediği orijinal görseller `data/first-outfit/` altında Git dışında tutulur. Bu seçim dosyası mevcut on ürünlük notebook'a doğrudan verilmez. Sentetik başlangıç mankeni built-in image_gen ile üretildi; FASHN sonucu değildir. Boy/kilo değerleri her kullanıcı için değişir; tek başlarına kesin vücut şekli veya beden uyumu sağlamazlar.

## Yerel iki parçalı deney

Proje sanal ortamında CUDA PyTorch ve FASHN kurulduktan sonra:

```powershell
python scripts/download_local_weights.py
.\.venv\Scripts\python.exe ai-worker/app/outfit.py
```

`outfit.py` aynı başlangıç mankeninden önce alt→üst, sonra üst→alt sıralarını ayrı çalıştırır. Her ara çıktı, son çıktı, hash, süre, bellek ve hata bilgisi `runs/outfit-.../` altında saklanır. İki sıra aynı deneyin alternatifleridir; ikinci sıra birincinin son görselinden başlamaz. Üstün doğruluğu ve altın korunması birlikte incelenmelidir. Üretilmiş görsel kalite başarısı anlamına gelmez.

8 GB GPU için yardımcı modeller CPU'da çalışır, ana ağırlıklar CPU'dan yüklenir ve CFG'nin koşullu/koşulsuz dalları ayrı yürütülür. Çözünürlük ve model ağırlıkları değiştirilmez. Bu değişiklikler upstream koduna dokunmadan subclass üzerinden uygulanır; ortam ve değişiklikler run kaydına yazılır. Tam kurulum/sürüm bilgisi başarılı denemedeki `pip-freeze.txt` dosyasındadır.

**Durum: yerel GPU inference çalıştırıldı; ilk iki parçalı kombin kıyafet kimliği testini geçemedi.** İki sıra ve üç ek hoodie ayarı denendi. [Gerçek deney bulguları](docs/first-outfit-results.md). Bu repository eski TryFit'ten kod veya tasarım içermez. Bu çalışma klasörünün adı `TryFit2`; bağımsız projenin adı TryFit Next'tir.

**İkinci tur:** aynı ürünün mankenli galeri fotoğrafı ve üst kıyafet koruma maskesiyle cep/yaka/etek ucu belirgin biçimde iyileşti. [Yeni deney ve yöntem](docs/outfit-followup.md). Tek örnek, genel kalite kapısı veya boy/kilo doğruluğu kanıtı değildir.

## İlk deneme

**Genişletilmiş test:** on farklı ürün ve üç yeni kombin çalıştırıldı. Ham modelin görsel ön değerlendirmesi 4/10; 8/10 eşiği karşılanmadı. Ayrı tam vücut kategori denemesinde trençkot iyileşti; ana oran değiştirilmedi. [Bulgular](docs/benchmark-10-results.md) · [Çevrimdışı görsel rapor](dist/validation-10/index.html).

**Kaynak kıyafeti ayırma:** aynı on kaynak için SAM2.1 ile araştırmacının noktalarla seçtiği kıyafet maskeleri eklendi. Görsel ön değerlendirme **7/10** oldu; 8/10 eşiği henüz karşılanmadı. Kaynaktaki iç üst ve aksesuarların aktarılmasını azaltmak için yalnızca kaynak kıyafet maskesi değiştirildi; orijinal poz ve VTON ayarları korundu. [Yöntem ve bulgular](docs/source-isolation-results.md) · [Önce/sonra raporu](dist/source-isolation/index.html). Bu aşama otomatik ürün seçimi değildir.

**Kesim için ek denemeler:** kalan üç üründe kaynak pozunu kaldırma, cutout dalı ve 50 adım/guidance 2.5 sınandı. Dokuz yeni çıktıdan hiçbiri kabul eşiğini geçmedi; genel sonuç **7/10** kaldı. Varsayılan yöntem değiştirilmedi. [Deney bulguları](docs/cut-probes-results.md) · [Tüm ek çıktılar](dist/cut-probes/index.html).

**İkinci model karşılaştırması:** CatVTON ayrı ortamda yerel GPU üzerinde çalıştırıldı. Aynı üç zor mankenli kaynak için ön değerlendirme **0/3**; iki ayrı gerçek düz ürün fotoğrafı/maske kontrolü de saklandı. CatVTON varsayılan yapılmadı; önceki **7/10** değişmedi. [Yöntem, kaynaklar ve sınırlamalar](docs/catvton-results.md) · [Ham ve repaint çıktıları](dist/catvton-comparison/index.html). CatVTON yalnızca ticari olmayan araştırma kullanımına açıktır.

**İki parçalı kombin:** tişört + pantolon, iki kaynakta da SAM maskesi kullanılarak birlikte üretildi. Ham ikinci çıktı ana önizleme seçildi; ek üst koruma kenarda kontur bıraktığı için ayrı gösterilir. [Gerçek kombin](dist/masked-outfit/outfit.png) · [Aşamalar](dist/masked-outfit/index.html) · [Bulgular ve sınırlar](docs/masked-outfit-results.md). Tek kombin genel kalite kapısını veya beden doğruluğunu kanıtlamaz.

**Üç farklı görünüm:** aynı kombin ince, orta ve dolgun sentetik mankenlerde altı yeni VTON aşamasıyla sınandı. İnce/orta görsel önizlemeleri makul; dolgun profilde ayak bölgesi hatası sürüyor. Ayak kompoziti sınır izi bıraktığı için düzeltme olarak kabul edilmedi. [Üç görünüm](dist/avatar-suite/three-outfits.jpg) · [Tam karşılaştırma](dist/avatar-suite/index.html) · [Yöntem ve promptlar](docs/avatar-suite-results.md). Bunlar hazır görsel profillerdir; boy/kilodan ölçülü vücut hesaplayan bir sistem değildir.

**Ayak için kontrollü takip:** yalnızca pantolon aşamasında hedef maskelemesi açılarak aynı üç üst çıktısı yeniden işlendi. Ayaklar üç yeni ham üretimde görünür kaldı; sonradan piksel yapıştırılmadı. Paça boyu kısalıyor ve üst etek ucu değişebiliyor; fiziksel oturuş doğrulanmadı. `avatar_suite.py --masked-bottom` isteğe bağlıdır, varsayılan değiştirilmedi. [Yeni üç kombin](dist/feet-input/three-outfits.jpg) · [Önce/sonra](dist/feet-input/index.html) · [Deney sınırları](docs/feet-input-results.md).

Yerel tekrar: `./.venv/Scripts/python.exe ai-worker/app/benchmark.py` ve `./.venv/Scripts/python.exe ai-worker/app/outfit_suite.py`. Tek kombin: `./.venv/Scripts/python.exe ai-worker/app/protect_outfit.py --selection evaluation/manifests/first-outfit.protected.json`.

1. [Colab notebook](notebooks/TryFitNext_FASHN_Quality_Test.ipynb) dosyasını [Google Colab](https://colab.research.google.com/) → File → Upload notebook ile açın.
2. Runtime → Change runtime type → ücretsiz GPU seçin. Kurulum hücrelerini sırayla çalıştırın.
3. [Manifest şablonunu](evaluation/manifests/trendyol-10.template.json) bilgisayarınızda `manifest.json` olarak kaydedin. On gerçek ürünün `product_url`, seçilen görselin `source_image_url` ve poz/örtülme bilgisinin `source_notes` alanını doldurun.
4. Fotoğraf kullanım iznini doğrulayıp `consent_confirmed` değerini `true` yapın. `person.jpg` ve manifestteki adlarla on mankenli ürün fotoğrafını hazırlayın. Görselleri notebook yükleme hücresinde manifestle birlikte seçin.
5. Önce tek tişört denemesi, sonra on ürünlük deney. Gerçek çıktı üretmeden başarı kaydı oluşturulmaz.
6. `review.csv` dosyasını indirip [değerlendirme protokolüne](docs/evaluation-protocol.md) göre doldurun, notebook'a geri yükleyin. Sonuç ZIP'ini indirin; `report.html` dosyasını arşivden çıkardıktan sonra açın.

Colab hesabında interaktif GPU oturumu ve gerçek görseller olmadan üretim yapılamaz. GPU tahsisi, inference süresi ve T4 belleğine sığma garantisi yoktur. Ücretsiz katman sürekli API sunucusu olarak kullanılmaz; hiçbir ücretli API çağrısı yoktur.

## Kapsam

- `ai-worker/app/experiment.py`: yerel Python deney runner'ı, ön kontrol, hash/süre/VRAM/hata kayıtları ve insan değerlendirmesi.
- `notebooks/`: bağımsız, runner gömülü Colab notebook'u.
- `evaluation/manifests/`: gerçek girdilerle doldurulacak on kategori şablonu; sahte ürün yok.
- `scripts/build_notebook.py`: runner ve manifestten notebook'u yeniden üretir.
- `ai-worker/tests/`: girdi doğrulama ve kalite kapısı davranış testleri; AI kalite testi değildir.

Yerel kontrol: `python -m unittest discover -s ai-worker/tests -v`

Notebook yeniden üretme: `python scripts/build_notebook.py`

İndirilen arşivi çıkardıktan ve `review.csv` dosyasını doldurduktan sonra değerlendirmeyi GPU olmadan yerel olarak da çalıştırabilirsiniz:
`python ai-worker/app/experiment.py evaluate "indirilen/runs/deney-klasoru"`

Tam tüketici uygulaması ve Chrome eklentisi genel kalite kapısını bekliyor. Seçilmiş örnekleri incelemek için sınırlı yerel araştırma ekranı eklendi: web → .NET 9 API → tek iş kuyruğu → bağımsız Python worker → gerçek PNG. Pantolon sonucu ham FASHN çıktısı, etek sonucu CatVTON repaint çıktısıdır. İş kayıtları yerel JSON dosyalarında tutulur; genel kullanıma veya ticari dağıtıma açılmadı.

**Son kontrollü deney:** hedef maskelemesini on ürünün tamamına açmak sonucu **5/10** seviyesine düşürdü; bütün kategorilere varsayılan yapılmadı. Önceki **7/10** koşusu korunuyor. [Bulgular](docs/target-mask-benchmark-results.md) · [Tam karşılaştırma](dist/target-mask-benchmark/index.html).

## Kaynak ve lisans

FASHN kaynağı `7c0f10af3f91ad4048fe9729c470a13ef905d25a` commit'ine sabitlenmiştir. Model revision'ları, ağırlık hash'leri ve `pip freeze` her deneyde kaydedilir. Paket listesi doğrulanmış CUDA ortam kilidi değildir; ilk çalışan Colab ortamı ayrıca sabitlenecek.

- [FASHN VTON 1.5](https://github.com/fashn-AI/fashn-vton-1.5): Apache 2.0 ana kod/ağırlıklar.
- [Human Parser lisansı](https://github.com/fashn-AI/fashn-human-parser/blob/main/LICENSE), [NVIDIA SegFormer lisansı](https://github.com/NVlabs/SegFormer/blob/master/LICENSE): araştırma/değerlendirme kısıtı. Resmî pipeline bu parser'ı maskless modunda da kullanır. Bu çalışma ticari dağıtım izni anlamına gelmez.
- [Colab kaynak sınırları](https://research.google.com/colaboratory/faq.html), [ONNX CUDA uyumluluğu](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html).

Kişisel fotoğraflar, sonuçlar, ağırlıklar ve vendor kodu Git dışında tutulur. Notebook veya çıktı arşivini herkese açık paylaşmayın; karşılaştırma panoları hedef fotoğrafı içerir.
