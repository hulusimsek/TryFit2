# Sweatshirt ve pijama altı

Kullanıcının ilk seçtiği lacivert sweatshirt ile siyah puantiyeli pijama altı, 175 cm / 65 kg etiketiyle kullanılan sentetik deneme mankeninde tekrar üretildi. Sweatshirt için aynı Trendyol ürününün mankenli galeri karesi, pijama için kullanıcının fotoğrafı kullanıldı. İki kaynakta da elle işaretlenen SAM maskeleriyle görünen kumaş seçildi.

| Ham çıktı | Pijama | Sweatshirt |
|---|---|---|
| Alt aşamada hedef maskesi açık | Puantiyeler belirgin, paçalar bileğin üstünde | Etek ucu ortadan yarılmış gibi görünüyor |
| Alt aşamada hedef maskesi kapalı | Puantiyeler ve bağcık belirgin, paçalar daha uzun | Orta yarık ortadan kalkıyor, fakat etek ucu yukarı çekiliyor ve ürünün bol kesimi tam korunmuyor |

Önizleme için ikinci ham görüntü seçildi. Bacakların üst yanlarında gri tayttan küçük izler görülebiliyor. Ürün kimliği açısından pijama tanınabilir. Sweatshirt’ün cep ve kapüşon çizgisi görünse de boyu ve hacmi ürün fotoğrafıyla yeterince eşleşmediği için kombin kalite kontrolünü geçmedi.

[Kaynaklar ve iki ham çıktı](../dist/first-outfit-review/comparison.jpg) · [Seçilen ham PNG](../runs/protected-outfit-c3013d50/04-bottom-target-unmasked.png)

Deney kaydı `runs/protected-outfit-c3013d50` altında. Her iki alt çıktıda aynı `01-top.png`, aynı pijama kaynağı, aynı kaynak maskesi, 30 adım, seed 42 ve guidance 1.5 kullanıldı. Alt aşamadaki hedef maskesi dışında ayar değiştirilmedi. Hash’ler `bottom-target-comparison.json` dosyasında. Panoda yer alan iki sonuç, modelin ham çıktılarıdır. `03-protected-outfit.png` dosyasında ayrıca üstü geri birleştiren araştırma çıktısı bulunur ve bel hizasında iz bırakır.

Projenin yerel Python ortamı ve çevrimdışı model önbelleğiyle:

```powershell
.\.venv\Scripts\python.exe ai-worker/app/extract_source.py evaluation/annotations/pajama-bottoms-1185662459.sam2.json runs/source-extraction-pajama-bottoms-1185662459-refined
.\.venv\Scripts\python.exe ai-worker/app/masked_outfit.py --selection evaluation/manifests/first-outfit.protected.json --masked-bottom
.\.venv\Scripts\python.exe ai-worker/app/masked_outfit.py --selection evaluation/manifests/first-outfit.protected.json
```

İlk komut yalnızca pijama maskesi klasörü henüz oluşmamışsa gerekli. Bu iki ürün araştırma önizlemesi olarak değerlendirildi ve yerel uygulama kataloğuna eklenmedi. Deneme mankeninin fiziksel ölçüleri doğrulanmış değildir.
