# Kararlar ve öğrenilen dersler

İnceleme tarihi: 11 Kasım 2026. Kararların ilk alındığı tarihler doğrulanmadığından burada tarihçe uydurulmaz. “Kural” AGENTS.md yönlendirmesi, “mevcut uygulama” kodla doğrulanan durum, “hedef” henüz uygulanmamış yönelimdir.

| ID | Durum | Karar ve gerekçe | Kanıt / sonuç |
| --- | --- | --- | --- |
| D01 | Kural | Yeni proje bağımsızdır; eski TryFit yalnızca okunur referanstır. | [AGENTS.md](../AGENTS.md). Eski kod veya tasarım otomatik taşınmaz. |
| D02 | Kural | Fotogerçekçi 2D try-on önceliklidir; 3D manken akışı eklenmez. | Eski depoda `MannequinViewer.tsx` vardır; yeni projenin araştırma yönü 2D'dir. |
| D03 | Mevcut uygulama + kural | .NET 9 backend dört Clean Architecture katmanını kullanır. İş kuralları iç katmanlarda, dosya/model erişimi adaptörlerde kalır. | [Mimari](architecture.md), `src/*/*.csproj`, `web/TryFit.Local/TryFit.Local.csproj`. Yeni proje/soyutlama ancak somut ihtiyaçla eklenir. |
| D04 | Hedef | Üretimde uzak GPU ve bağımsız Python worker; backend için yerel GPU zorunluluğu yok. | Bugünkü `PythonTryOnEngine` yerel süreçtir. Uzak adaptör/dağıtım TODO; mevcut yerel araştırma üretim mimarisi diye sunulmaz. |
| D05 | Kural + mevcut uygulama | Hazır/küratörlü görüntü inference başarısı olarak dönülmez. Hata açıkça başarısız iş olur. | Eski `HuggingFaceTryOnService.cs` ağ hatası/başarısız akışta hazır URL ile `Success=true` döndürüyor. Yeni adaptör süreç sonucu, PNG ve hash kontrol ediyor. Dosya kontrolü görsel kalite kanıtı değildir. |
| D06 | Araştırma yöntemi | Başarı gerçek ürün girdileri, kayıtlı çıktılar ve ayrı kalite değerlendirmesiyle ölçülür. | [Protokol](evaluation-protocol.md): sekiz puanın her biri en az 3, kritik hata ve seçilmeyen parça değişimi yok; on örnekte en az sekizi geçmeli. Olumsuz koşular korunur, farklı koşuların iyi örnekleri tek oran yapılmaz. |
| D07 | Mevcut araştırma tercihi | FASHN + araştırmacı destekli SAM kaynak maskesi korunur; otomatik ürün ayırma iddiası yoktur. | [Kaynak izolasyonu](source-isolation-results.md): görsel ön sonuç 7/10; genel kalite kapısı geçilmedi. |
| D08 | Deney sonucu | Hedef maskeleme tüm kategorilere varsayılan yapılmaz. Yerel kombin ekranında üst hedef maskesiz, alt hedef maskelidir. | [On ürün kontrolü](target-mask-benchmark-results.md) 5/10; [ayak kontrolü](feet-input-results.md) üç örnekte iyileşme. Yerel karma protokolün bağımsız on ürünlük oranı ölçülmedi. |
| D09 | Deney sonucu | CatVTON varsayılan modele geçirilmedi. | [Karşılaştırma](catvton-results.md): üç zor mankenli kaynakta ön değerlendirme 0/3; tüm kurulumlar için başarısızlık iddiası değildir. Ayrı ortam ve farklı hazırlık karşılaştırmayı sınırlar. |
| D10 | Kapsam sınırı | Hazır görsel profil fiziksel beden simülasyonu değildir; boy/kilodan kesin ölçü veya beden uygunluğu iddia edilmez. | Eski `FitAdvisorService.cs` tahmini vücut formülleri ve üretilmiş standart beden matrisleri kullanıyor. Bu kod gerçek ürün ölçüsü/fit doğrulaması kanıtı değildir; yeni projede böyle bir özellik tamamlanmadı. |
| D11 | Yerel araştırma tercihi | Dört ürün, üç profil, JSON kayıt ve tek tüketicili bellek kuyruğu yeterlidir. | [Yerel ekran](local-app.md). Kalıcı dağıtık kuyruk/veritabanı bugünkü kapsam için eklenmez; çok sunuculu güvenilirlik sağlandığı iddia edilmez. |
| D12 | Kural / yayın öncesi açık iş | Gizlilik, model bileşenlerinin lisansları ve bütçe dağıtımı sınırlar. | Görseller/sonuçlar Git dışında; bu tek başına erişim kontrolü değildir. Depodaki lisans notları ticari kullanım engelleri bildiriyor. Güncel dağıtım uygunluğu ayrıca doğrulanmalı; ücretli kaynak için açık onay gerekir. |

## Eski TryFit referansının sınırları

Salt okunur incelenen depo: `../TryFit`. README yalnızca proje başlığı içeriyor; önceki sohbetler veya kullanıcı test raporları bu incelemede mevcut değil. Dolayısıyla “önceki projede kullanıcılar şunu yaşadı” gibi doğrulanmamış olaylar kaydedilmedi.

| İncelenen eski kaynak | Kodda görülen durum | Yeni projeye çıkarılan ders |
| --- | --- | --- |
| `src/TryFit.Infrastructure/ExternalServices/HuggingFaceTryOnService.cs` | Harici Gradio çağrısı ve hata durumunda başarılı sayılan küratörlü görsel. | Servis erişilebilirliği ile gerçek üretim ve ürün doğruluğunu ayrı doğrula; hata yerine örnek gösterme. Eski servisin bugün erişilebilirliği sınanmadı. |
| `src/TryFit.Application/Services/FitAdvisorService.cs` | Boy/kilodan tahmini ölçüler, kategori/başlıktan beden tabloları ve sabit uyum skoru. | Ölçülmemiş tahminleri kişiye/ürüne özel doğruluk gibi sunma. |
| `src/TryFit.Client/src/components/3d/MannequinViewer.tsx` | 3D görüntüleyici dosyası mevcut. | Yeni kapsamı 2D kalite araştırmasında tut; 3D kod varlığı kıyafet aktarım kalitesi kanıtı değildir. |
| `src/TryFit.Extension/content.js` | Ürün bağlantısını yerel istemci adresine açan akış. | Eski eklenti varlığı yeni eklentinin tamamlandığı anlamına gelmez; ayrı istemci sözleşmesi doğrulanmalı. |

Bu dersler kaynak incelemesinden çıkarımlardır; eski uygulama bu görevde çalıştırılmadı ve hiçbir dosyası değiştirilmedi.

## Açık kararlar

- TODO: Uzak worker iletişim ve depolama sözleşmesi; sağlayıcı, maliyet ve bağımsız dağıtım doğrulaması.
- TODO: Kullanıcı kimliği, iş/görsel sahipliği ve saklama/silme politikası.
- TODO: Yayın için model ve tüm yardımcı bileşenlerin lisans uygunluğunun doğrulanması. Bu belge hukuki izin yerine geçmez.
- TODO: Bağımsız değerlendirici, farklı hedef kişiler/pozlar ve iki parçalı kombinler için genişletilmiş kalite kapısı.

Yeni kararda problem, seçenekler, seçilen en basit çözüm, kanıt, sonuç ve yeniden değerlendirme koşulu kaydedilmelidir.
