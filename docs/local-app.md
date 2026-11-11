# Yerel kombin ekranı

Çalışan adres: http://127.0.0.1:5187 . Bir hazır profil, bir üst ve bir alt seçip **Kombini dene** düğmesine basın. Üretim bitince gerçek PNG görüntülenir ve indirilebilir. Bu bilgisayardaki iki doğrulanmış deneme yaklaşık 79–87 saniye sürdü; süre donanım ve sıraya göre değişir.

Uygulama kapalıysa proje kökündeki `Start-TryFit.cmd` dosyasını çift tıklayın, ardından yukarıdaki adresi tarayıcıda açın. Uygulama zaten çalışıyorsa başlatıcı mevcut sayfayı açar. Yeni sunucunun açıldığı komut penceresini açık tutun; kapatmak için Ctrl+C kullanın. Bu bilgisayarda .NET 9, Python `.venv`, yerel model ağırlıkları ve kaynak görseller hazırdır; başlatıcı bu büyük bağımlılıkları indirmez.

## Çalışan kapsam

- Üç sentetik hazır görünüm; bunlar boy/kilodan hesaplanan ölçülü vücutlar değildir. 175/65 gibi önceki deney etiketleri fiziksel doğruluk sağlamaz.
- Dört seçilmiş gerçek ürün: tişört, desenli bluz, geniş pantolon, pileli etek. Bir üst ve bir alt birlikte üretilir.
- Gerçek iş sırası, işlem aşaması, geçen süre, sonuç indirme ve sayfa yenilenince son işi geri getirme.
- Etekte varsayılan açık **Üstü eteğin içine al** seçimi; uzun üst dışarıda bırakılırsa kemeri örtebilir. Bu seçim üstün alt kısmının giyim biçimini değiştirir, orijinal etek ucunun aynen korunması anlamına gelmez.
- Yeni Trendyol bağlantısından otomatik ürün alma veya kişisel fotoğraf yükleme bu sürümde bulunmaz. İlk paylaşılan hoodie/pijama bu dört ürün arasında değildir.

## Uygulama ve doğrulama

.NET 9 API yalnızca `127.0.0.1:5187` üzerinde dinler. Tek okuyuculu iş kuyruğu GPU işlerini sırayla ayrı Python süreçlerine gönderir. İş kayıtları `runs/local-jobs/<id>/` altında JSON olarak saklanır. Yeniden başlatmada bitmiş işler geri yüklenir, kesilen işler başarısız olarak işaretlenir. En fazla üç aktif/bekleyen iş kabul edilir. Uygulama internete yayımlanmadı.

`ai-worker/app/local_job.py`, yerel FASHN modelini ve önceden hazırlanmış SAM kaynak maskelerini kullanır. Üst aşaması hedef maskesizdir. Pantolon yolu FASHN üst + hedef maskesiz alt ve ayak/zemin korumasıdır. Etek yolu artık yeni üst üreten FASHN süreci, ardından ayrı `.venv-catvton` sürecidir; ilk süreç çıkınca GPU belleği bırakılır. Üstün gerçek ayrıştırmasıyla o işe özel alt maske/koruma hazırlanır. `01-top.png`, `02-skirt-raw.png`, `02-skirt-repaint.png` ve hash'li `skirt-handoff.json` aynı iş dizininde saklanır. Ekranda etek için repaint PNG gösterilir: düzenlenmeyen bölgeler hedeften kopyalanır, etek gerçek CatVTON üretimidir. Hata halinde hazır sonuç kullanılmaz. İş tamamlanmadan PNG imzası ve SHA-256 doğrulanır. Modeller çevrimdışı çalışır; ücretli API çağrısı yoktur.

Koruma, açık üst gövde tenini (`torso`) de kapsar; böylece alt parça eklenirken açık karın bölgesinin yeni kıyafetle kapanması azaltılır. [Kısa üst kontrolü ve devam eden toka kaybı](waist-control-results.md). Bu kontroldeki sentetik kısa üst hedefi yerel profil/ürün listesine eklenmedi.

Etek entegrasyonunun güncel doğrulaması: [ekrandan gerçek üretim, seçim kaydı ve kalan sınırlar](skirt-app-integration.md). Önceki araştırma çıktıları yeni işlerin yerine kullanılmaz. Sonuç bağlantıları `?job=<id>` ile açılabilir; eski yöntemle tarayıcıda saklanmış önizleme yeni yöntemin sonucu diye otomatik yüklenmez. Aşağıdaki ilk ekran doğrulama kaydı önceki sürüme aittir.

Tarayıcıda dolgun profil + tişört + pantolon işi tamamlandı; indirme bağlantısı ve başlangıç görseli karşılaştırması görüldü. Ekran görüntüsü: `dist/local-app/screenshot.jpg`. API üzerinden orta profil + bluz + etek de 78,6 saniyede tamamlandı. Bluz/etek çıktısında iki parça ve ayaklar görünür; eteğin kemer/toka ayrıntısı korunmadığından bunu kusursuz ürün aktarımı olarak değerlendirmiyoruz. Görsel dosyaların hash'leri ve HTTP kontrolleri `runs/local-app-validation.json` içindedir.

Python davranış testleri: 40 test, bir isteğe bağlı CatVTON testi atlandı. .NET derlemesi sıfır hata/uyarıyla tamamlandı. Geçersiz profil ve dosya yolu içeren ürün kimlikleri HTTP 400 ile reddedildi. Masaüstü tarayıcı görünümü doğrulandı; mobil cihaz testi yapılmadı.

Bu sınırlı araştırma ekranı genel kalite kapısının geçildiği anlamına gelmez. On ürünlük kaynak maskeli önceki koşu 7/10, bütün hedefleri maskeleyen ayrı kontrol 5/10'dur; ikisi de 8/10 eşiğinin altında. İki parçalı karma yöntemin on ürünlük bağımsız başarı oranı ölçülmedi. Gerçek beden uyumu, kumaş fiziği ve boy/kilo eşlemesi doğrulanmadı. İnsan ayrıştırıcısının araştırma lisansı kısıtı devam eder; ticari dağıtıma hazır değildir.
