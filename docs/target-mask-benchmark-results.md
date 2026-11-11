# On üründe hedef maskeleme kontrolü

Yeni koşu: `runs/20261110T134441Z-be46a99c`. Önceki SAM kaynak maskeli kontrol: `runs/20261110T095148Z-cf9135a6`. On gerçek üretim yaklaşık 362 saniyede tamamlandı. Tek kontrollü değişken `segmentation_free=True` yerine `False`: hedef kişi maskesi de kullanıldı. Kaynak/hedef görselleri, SAM maskeleri, kategoriler, kaynak pozu, seed 42, 30 adım ve guidance 1.5 korundu. Sonuçlara piksel kompoziti uygulanmadı.

Asistanın görsel ön incelemesi **5/10**; önceki koşu **7/10**. Bağımsız kullanıcı değerlendirmesi değildir ve 8/10 kalite kapısı geçilmedi. Önceki çıktı ve puanlar değiştirilmedi; farklı koşuların iyi örnekleri birleştirilerek yeni bir başarı oranı üretilmedi.

| Ürün | Yeni karar | Başlıca bulgu |
|---|---|---|
| Oversize hoodie | Başarısız | Bol kesim kısa/dar kalıyor. |
| Tişört | Geçti | Yaka/kısa kol makul; küçük bel değişimi var. |
| Desenli bluz | Geçti | Askı/desen makul; katlanma ve etek ucu yaklaşık. |
| Trençkot | Başarısız | Uzun kuşaklı giysi kısa üste dönüşüyor; hedef altta kot ayrıntıları uyduruluyor. |
| Kot ceket | Başarısız | Kollar kısa; seçilmeyen altın beli değişiyor. |
| Uzun elbise | Geçti | Uzun kol/etek makul; boy yaklaşık. |
| Dar elbise | Geçti | Midi siluet makul; beden uyumu ölçülmedi. |
| Geniş pantolon | Geçti | Ayaklar görünür; paça kısa, bel ayrıntısı örtülü. |
| Etek | Başarısız | Beldeki kemer/toka uzun hedef üstle örtülüyor, doğrulanamıyor. |
| Fermuarlı kapüşonlu üst | Başarısız | Açık dış katman kapanıyor/daralıyor; iç üst kayboluyor. |

Hedef maskeleme bütün kategoriler için varsayılan yapılmadı. Yerel deneme ekranının üstte hedef maskesiz/altta hedef maskeli iki aşamalı protokolü farklı bir deneydir; bu 5/10 oranı ona ait değildir. Önceki ayak kontrolünde iyileşme görülmesi tüm ürünlerde iyileşme anlamına gelmedi.

Tam önce/sonra görselleri ve puanları: `dist/target-mask-benchmark/index.html`. Tekrar üretim: `.venv/Scripts/python.exe ai-worker/app/target_masked_benchmark.py`; rapor: `.venv/Scripts/python.exe scripts/build_target_mask_report.py runs/20261110T134441Z-be46a99c`. Kaynak maskeleri araştırmacı desteklidir; otomatik ürün alma ve ölçülü manken üretimi bu deneyin kapsamında değildir.
