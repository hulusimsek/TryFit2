# On ürün ve üç kombin: doğrulama turu

On gerçek Trendyol ürünü aynı sentetik hedef kişi üzerinde FASHN VTON v1.5 ile yerel GPU'da çalıştırıldı. **Görsel ön değerlendirmede 4/10 örnek geçti; önerilen 8/10 eşiği karşılanmadı.** Bu oran bağımsız insan paneli veya objektif otomatik metrik değil, asistanın kayıtlı görsel değerlendirmesidir.

Sekiz görsel puana ek olarak kombin bütünlüğü için seçilmeyen kıyafet/aksesuar değişimi ayrı başarısızlık koşuludur (`untargeted_changes`). Vücut şekli puanıyla karıştırılmaz. Gerçek beden uyumu ölçülmedi.

| Kategori | Ön sonuç | Başlıca gözlem |
|---|---|---|
| Oversize hoodie | Başarısız | Yaka/cep makul; bol kesim ve ürün boyu tam korunmuyor. |
| Tişört | Geçti | Siyah kısa kol, bisiklet yaka ve genel kesim makul. |
| Desenli bluz | Geçti | Askılar, küçük çiçek deseni ve sivri etek formu genel olarak korunuyor. |
| Trençkot (`tops`) | Başarısız | Uzun kuşaklı ürün kısa cekete dönüşüyor. |
| Kot ceket | Başarısız | Kol boyu değişiyor; kaynak iç crop ve kolye de taşınıyor. |
| Uzun elbise | Başarısız | Elbise makul; kaynak çizme ve bilek aksesuarı da taşınıyor. |
| Dar elbise | Geçti | Midi boy/yaka/siluet makul; kaynak gözlüğü ve ayakkabısı taşınmamış. |
| Geniş pantolon | Başarısız | Pantolon makul; model seçilmeyen tişörtü kısaltıp beli açıyor. |
| Etek | Geçti | Pile, kemer ve genel boy makul; bacak ölçüleri doğrulanmış değil. |
| Fermuarlı kapüşonlu üst | Başarısız | Ana üst makul; kaynak siyah iç crop da taşınıyor. |

Geniş pantolon kaynağında AI üretim etiketi var. Gerçek bir ürün kaydıdır; bu görselin gerçek fotoğraf olduğu iddia edilmez. Diğer kaynakların çekim kökeni bağımsız olarak doğrulanmadı.

## Üç yeni kombin

- **Tişört + pantolon:** üst kısalması/çıplak bel sorunu semantik korumayla engellendi. Üst etek ucunda ince kontur izi var; bel detayı kısmen örtülüyor.
- **Bluz + etek:** sivri bluz etek ucu korunuyor; kemer kısmen örtülüyor. Bel sınırı ve sağ kenardaki küçük ayrıntı ayrıca incelenmeli.
- **Kot ceket + pantolon:** ceket etek ucu korunuyor, ama kaynak iç crop/kolye aktarımı sürüyor. İlk aşamanın yanlış parçaları da korunuyor.

Her çift aynı başlangıç hedefinden başlatıldı. Ham ikinci çıktı ile koruma uygulanmış çıktı ayrı saklandı. Üçünde de korunan iç pikseller ilk üst çıktısıyla, maskeden uzak pikseller ham alt çıktısıyla birebir aynı olarak kontrol edildi. Bu, maskenin doğru kıyafeti seçtiğini veya görüntünün fotogerçekçi olduğunu kanıtlamaz. Kombinler genel kalite kapısını geçmiş sayılmadı.

## Ayrı trençkot deneyi

Aynı kaynak/hedef ve diğer aynı ayarlarla kategori `tops` yerine `one-pieces` seçildi. Bu ayar kaynak/hedef hazırlığını da değiştiriyor: `tops` kaynak hazırlığında kuşak etiketi çıkarılırken tam vücut hazırlığı kuşağı içeriyor. Bu tek örnekte uzunluk ve kuşak belirgin biçimde düzeldi; fular/eldiven de eklenmemiş görünüyor.

Bu deney 4/10 oranına eklenmedi. Tüm uzun dış giyimi otomatik bu kategoriye yönlendirmek doğrulanmış değildir; açık ceket/katmanlı örneklerle tekrar sınanmalı.

## Yeniden üretim ve kapsam

Ana run: `runs/20261110T003636Z-688ebfd6/`. Kaynak/model hash'leri, commit, ortam, süre/VRAM, tüm çıktılar ve `review.csv` saklandı. Ayrı kategori deneyi: `runs/20261110T004724Z-75b35e06/`. Üç kombin: `runs/latest-outfit-suite.json`.

```powershell
./.venv/Scripts/python.exe ai-worker/app/benchmark.py
./.venv/Scripts/python.exe ai-worker/app/outfit_suite.py
./.venv/Scripts/python.exe ai-worker/app/benchmark.py --manifest evaluation/manifests/trench-coverage-probe.json
python scripts/build_validation_report.py runs/20261110T003636Z-688ebfd6 --probe runs/20261110T004724Z-75b35e06
```

Genel kombin runner'ı artık `--selection` ile avatar ve ürün manifesti alır. Boy/kilo sabit kodlanmış değildir; hedef görüntüsünün bu ölçüleri fiziksel temsil etmesi henüz sağlanmadı. Aynı mankene farklı boy/kilo etiketi vermek beden modellemesi değildir.

24 yerel kontrol geçti. Taşınabilir HTML raporunun yerel resim/dosya bağlantıları kontrol edildi. Ham ve maskeli sonuçlar birlikte gösterilir. Sonraki teknik odak: ürün rolü/vücut kapsamasını ayırmak ve seçilmiş kıyafeti kaynaktaki iç üst/aksesuar/ayakkabıdan ayırmak. Kalite eşiği karşılanmadan tam backend/frontend geliştirilmedi.
