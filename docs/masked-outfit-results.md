# Seçilen iki kıyafeti birlikte uygulama

Tişört ve geniş pantolon, son SAM kaynak maskeleri iki parçaya da uygulanarak aynı sentetik mankende yeniden üretildi. Çalışma `runs/protected-outfit-aa50fe41` içinde; önceki maskesiz kaynaklı çift `runs/protected-outfit-90dfb46e` değiştirilmedi. Her aşama 30 adım, guidance 1.5, seed 42, BF16 FASHN VTON kullandı. Üst aşama 36.65 sn, alt aşama 36.86 sn sürdü.

**Ham iki-parça sonucu görsel önizleme olarak kullanılabilir görünüyor; bel/düğme ayrıntıları ve sınırlar ayrıca incelenmeli.** Bu, bağımsız panel kararı veya genel kalite kapısı değildir. Genel 7/10 sonucu değişmedi. Boy/kilo kullanıcıya göre değişen alanlardır; aynı mankenin 175 cm / 65 kg ölçülerini fiziksel olarak temsil ettiği doğrulanmadı.

Ham sonuçta siyah kısa kol/bisiklet yaka tişört ve siyah geniş paça birlikte üretildi. Bu koşuda pantolon eklenmesi beli açıkta bırakmadı. Kaynak beyaz kıyafetler, kemer ve spor ayakkabı eklenmedi. Pantolonun bel bandı/düğmesi tişörtle örtülüyor ve ayrıntı kaybediyor; iki siyah parçanın sınırı düşük kontrastlı. Kaynak pantolon görseli ürün sayfasında AI üretimi olarak etiketlidir; gerçek ürün kaydıdır, gerçek çekim olduğu iddia edilmez.

Üst koruma uygulanmış sürüm de saklandı. Kontrol edilen 57204 iç piksel ilk üst çıktısından, 435127 dış piksel ham ikinci çıktıdan birebir geldi; maksimum kanal hatası ikisinde de 0. Ancak bu sürümde tişört alt kenarında ince açık/gri kontur ve küçük kenar izleri görüldü. Piksel koruma kontrolünün geçmesi maske sınırının görsel olarak doğru olduğunu kanıtlamaz. **Ana önizleme bu nedenle ham `02-bottom-raw.png` olarak seçildi.** İki sürüm raporda yan yana gösterilir; görsel başarı gibi sunulup gizlenen işlem yoktur.

`masked_outfit.py` kaynak görüntüsünü boyut + RGB SHA256 ile maskesine bağlar. Kaynak dosya/maske hash'i, kimlik, kategori ve geometri doğrulanır. Her inference kendi maskesini kullanır; dışarıdaki üçüncü hedef ayrıştırma çağrısı gerçek insan ayrıştırıcısına gider. Değişmiş kaynak/maskeler ve yanlış eşleşmeler reddedilir. Yöntem ve kaynak maskesi provenance bilgileri başlangıç run kaydına eklenir.

```powershell
# Proje içi HF_HOME ve offline ortam değişkenleri ile:
./.venv/Scripts/python.exe ai-worker/app/masked_outfit.py --selection evaluation/manifests/tshirt-trousers.outfit.json
./.venv/Scripts/python.exe scripts/build_masked_outfit_report.py runs/protected-outfit-aa50fe41
```

34 yerel kontrol çalıştı; CatVTON'a özel bir kontrol kendi ortamı gerektirdiği için atlandı. Yeni kontroller her parçada doğru maskenin kullanılmasını, koruma için gerçek ayrıştırıcının kullanılabilir kalmasını ve değişmiş maskenin GPU yüklenmeden reddedilmesini sınar. FASHN insan ayrıştırıcısının araştırma lisansı kısıtı sürer. Kaynak seçimi otomatik değildir; kullanıcı arayüzü veya ölçülü beden modellemesi bu deneyde geliştirilmedi.

[Gerçek kombin görseli](../dist/masked-outfit/outfit.png) · [Kaynak ve ara aşamalarla rapor](../dist/masked-outfit/index.html) · [Taşınabilir ZIP](../dist/masked-outfit-results.zip).
