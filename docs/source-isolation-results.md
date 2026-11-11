# Kaynak görselden seçilmiş kıyafeti ayırma

SAM2.1 Hiera Base+ ile, aynı on ürünün görünen kumaşı kaynak fotoğraftaki diğer kıyafetlerden ve aksesuarlardan ayrıldı. Noktalar araştırmacı tarafından elle seçildi; bu aşama otomatik ürün tanıma değildir. Boy/kilo ile ölçülü manken üretimi bu deneyin kapsamı değildir.

## Sonuç

**Asistanın görsel ön değerlendirmesi 4/10'dan 7/10'a çıktı. 8/10 kalite eşiği karşılanmadı.** Bağımsız insan paneli veya otomatik doğruluk ölçümü değildir. Eski 4/10 kaydı değiştirilmedi. Bütün on örneğin aynı sabit ayarlı yeni sonucu puanlandı; ilk ceket pilotu bu orana eklenmedi.

| Ürün | Yeni ön sonuç | Gözlem |
|---|---|---|
| Lacivert oversize hoodie | Başarısız | Cep/yaka var; boy ve bol kesim yeterince korunmuyor. |
| Tişört | Geçti | Kısa kol, yuvarlak yaka ve genel kesim makul. |
| Desenli bluz | Geçti | Askılar, desen ve sivri etek ucu makul. |
| Trençkot | Geçti | Aynı `tops` kategorisinde uzun gövde ve kuşak geri geldi; fular/eldiven eklenmedi. |
| Kot ceket | Başarısız | Beyaz iç crop/kolye/askı aktarımı yok; kollar hâlâ kısa. |
| Uzun elbise | Geçti | Elbise korunuyor; kaynak çizme ve bileklik artık eklenmiyor. |
| Dar elbise | Geçti | Midi siluet ve yaka makul; gözlük/sandalet eklenmedi. |
| Geniş pantolon | Geçti | Bu turda gri tişört beli açmıyor; kaynak beyaz üst ve spor ayakkabı eklenmedi. |
| Etek | Geçti | Pile, kemer ve mini boy makul; sağ kenarda küçük sapma var. |
| Kahverengi fermuarlı üst | Başarısız | Siyah iç crop aktarımı yok; fakat kaynakta açık olan fermuar kapanıyor, gri iç üst kayboluyor. |

Bu kontrollü örneklerde yalnızca kaynak maskesi değişti. Gri tişörtün pantolon denemesinde korunması tüm girdilerde garanti değildir; kahverengi üstte katman koruma sorunu sürer. Ürün hacmi/kol uzunluğu ve katmanların ayrı korunması sonraki çözülmemiş sorunlardır. Yeni iki parçalı kombinler bu turda yeniden çalıştırılmadı; önceki üç kombin ayrı deneyler olarak kalır.

[Çevrimdışı önce/sonra raporu](../dist/source-isolation/index.html) ve [taşınabilir ZIP](../dist/source-isolation-results.zip) kaynak, önceki çıktı, seçilmiş kumaş ve yeni VTON çıktısını yan yana içerir. On maskenin kaynak/maske hash'leri ve bütün anotasyon noktalarına uyumu ayrıca doğrulandı. 28 yerel kontrol geçti; bunlar görsel kalite veya gerçek beden uyumunu kanıtlamaz.

## Kontrollü yöntem

FASHN VTON 1.5, kaynak fotoğraf, kaynak pozu, sentetik hedef, kategoriler, seed 42, 30 adım ve guidance 1.5 sabit tutuldu. İnsan ayrıştırıcısının yalnızca kaynak üzerindeki ikinci çağrısı SAM maskesinden gelen etiketlerle değiştirildi. Hedef ayrıştırıcısı ve orijinal kaynak fotoğraftan DWPose korunur. Upstream kaynak değiştirilmez. `SourceMaskParser` iki çağrı sırasını, kategori ve geometrisini denetler, her denemeden sonra maskeyi sıfırlar. Maskesiz hedef ve mankenli ürün dışında kullanımı reddeder.

İlk çoklu aday maskelerinde kumaş içinde boşluklar görüldü. Sadece float32 kullanmak bunları çözmedi. Son protokol: ilk olumlu noktadan en yüksek tahmini IoU adayı, ardından bütün olumlu/olumsuz noktalarla önceki logits'i kullanan iki tek-maskeli düzeltme. Bu maske hazırlama protokolü VTON karşılaştırmasından önce on kaynakta görsel incelendi. Hiçbir VTON sonucu seçilerek saklanmadı; ilk ceket pilotu ayrı tutuldu.

Maskeler görünür kumaşı seçer; el, saç ve çantanın arkasında kalan doku yeniden oluşturulmaz. SAM'in tahmini IoU puanı gerçek anotasyonla ölçülmüş IoU değildir. Maske geçişi, işaretli bütün olumlu/olumsuz noktalara uyum gerektirir; bu kontrol piksel düzeyinde bütün maskenin doğru olduğunu kanıtlamaz. Reddedilen ilk adaylar `runs/source-extraction-*-diagnostic` altında tutuldu.

Anotasyonlar `evaluation/annotations/*.sam2.json` içinde, kaynak SHA256 ve normalize noktalarla saklanır. Her çıkarımın `extraction.json` kaydı ağırlık SHA256, SAM commit, aday puanı, maske SHA256 ve yöntemi içerir. SAM GPU'dan çıkarıldıktan sonra VTON ayrı işlemde yüklenir.

## Yeniden üretim

SAM2 commit: `2b90b9f5ceec907a1c18123530e92e794ad901a4`. Checkpoint SHA256: `a2345aede8715ab1d5d31b4a509fb160c5a4af1970f199d9054ccfb746c004c5`. Kaynak: [resmî SAM2 deposu](https://github.com/facebookresearch/sam2), [resmî ağırlık](https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt).

Windows kurulumunda `SAM2_BUILD_CUDA=0` ve `pip install --no-build-isolation -e ./vendor/sam2` kullanıldı. Opsiyonel CUDA küçük boşluk/benek düzeltmesi kullanılmadı. Test edilmiş ortam `ai-worker/requirements-windows-tested.txt` içinde güncellendi.

```powershell
./.venv/Scripts/python.exe ai-worker/app/extract_source.py evaluation/annotations/denim-jacket.sam2.json runs/new-denim-extraction
./.venv/Scripts/python.exe ai-worker/app/masked_benchmark.py --case denim-jacket --extraction runs/new-denim-extraction
```

Tek ürün denemesi genel kalite kapısını geçiremez. Ana eski koşu `runs/20261110T003636Z-688ebfd6` değiştirilmedi. Yeni on ürünlük koşu `runs/20261110T095148Z-cf9135a6` içinde ayrı tutulur.

On ürünü birlikte tekrar çalıştırmak için aynı `masked_benchmark.py` çağrısına her ürün için bir `--case ID --extraction KLASÖR` çifti eklenir. Bu turda klasörler `runs/source-extraction-ID-refined` olarak kaydedildi. Nihai çıktıları puanladıktan sonra `python scripts/build_source_mask_report.py runs/20261110T095148Z-cf9135a6` komutu çevrimdışı önce/sonra HTML raporunu ve ZIP'i üretir.

SAM2 kodu/ağırlıkları Apache 2.0'dır. FASHN insan ayrıştırıcısının araştırma/değerlendirme lisansı kısıtı devam eder; bu değişiklik ticari dağıtım izni sağlamaz.
