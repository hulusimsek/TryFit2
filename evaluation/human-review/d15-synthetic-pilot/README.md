# TryFitNext — D15 Kalite Değerlendirme Yönergesi ve İnceleme Kılavuzu

Bu değerlendirme paketi, TryFitNext 2D Sanal Kıyafet Deneme (Virtual Try-On) sisteminin teknik pilot çıktılarını bağımsız, nesnel ve tarafsız bir gözle incelemeniz için hazırlanmıştır.

Paket içerisinde 9 farklı anonim deneme vakası (`H01` – `H09`) yer almaktadır. Değerlendirmenizi tamamlamak için lütfen bu kılavuzu dikkatle okuyunuz ve `degerlendirme-formu.xlsx` (veya `degerlendirme-formu.csv`) dosyasını doldurunuz.

---

## 1. Görsel Panellerinin Anlamı

`cases/` klasöründe her vaka için iki adet görsel bulunmaktadır:
1. **`H0X_comparison.jpg`:** Sürecin tüm aşamalarını yan yana gösteren karşılaştırma paneli.
2. **`H0X_result.png`:** Modelin ürettiği nihai sonucun tam çözünürlüklü (`576×859`) orijinal görseli. Kumaş dikişleri, toka kalıntıları, pile derinliği ve sınır pikselleri gibi ayrıntıları yakından incelemek için mutlaka bu dosyayı açınız.

Karşılaştırma panelleri vakanın giysi türüne göre 3 veya 4 bölümlüdür:

### A. Üç Panelli Vakalar (Yalnız Üst Giyim):
- **Panel 1 (En Sol - `TARGET`):** Kıyafet denemesi yapılacak hedef avatar/kişi (gri basic tişört ve gri tayt giymektedir).
- **Panel 2 (Orta - `TOP SOURCE`):** Hedef kişiye giydirilmesi istenen gerçek kaynak kıyafet fotoğrafı (siyah basic bisiklet yaka tişört).
- **Panel 3 (En Sağ - `RESULT`):** Yapay zekâ modelinin ürettiği sanal deneme sonucu.

### B. Dört Panelli Vakalar (İki Parçalı Kombin — Üst Tişört + Alt Etek):
- **Panel 1 (En Sol - `TARGET`):** Temel hedef avatar/kişi.
- **Panel 2 (Sol-Orta - `TOP SOURCE`):** Kombinin birinci aşamasında uygulanan kaynak üst kıyafet (siyah tişört).
- **Panel 3 (Sağ-Orta - `SKIRT SOURCE`):** Hedef kişiye giydirilmesi istenen kaynak etek fotoğrafı (siyah, derin pileli, kalın kemerli ve metal tokalı mini etek).
- **Panel 4 (En Sağ - `RESULT`):** Yapay zekâ modelinin ürettiği iki parçalı sanal deneme sonucu (tişört eteğin içine sokulmuş veya eteğin üzerine dökülmüş olabilir).

---

## 2. Kalite Kabul Kuralı (D15 Kararı)

TryFitNext projesinde kabul edilen **D15 Kalite Kararı** uyarınca:
> **Bir sanal deneme sonucu yalnızca kıyafet kategorisi (ör. etek) veya genel rengi doğru olduğu için başarılı kabul edilemez.**  
> Kaynak kıyafette fiilen bulunan karakteristik tasarım özellikleri korunmalıdır.

Lütfen her vakayı incelerken şu boyutlara özellikle dikkat ediniz:

1. **Renk ve Desen:**
   - Kaynak ürünün özgün rengi korunmalıdır.
   - Siyah bir ürünün sıcak bronz, kahverengi veya soluk griye kayması bir kalite ihlalidir.
2. **Kesim ve Silüet:**
   - Kıyafetin boyu, formu ve kalıbı (ör. mini A-line silüet, bisiklet yaka, kısa kol) doğru yansıtılmalıdır.
3. **Kemer ve Toka Aksesuarları:**
   - Kaynak kıyafette **belirgin bir kemer, kumaş köprüleri veya metalik toka** varsa, bunların sonuçta kaybolması, silinmesi veya detaysız sıradan bir bel çizgisine dönüşmesi kabul edilemez.
4. **Pileler ve Kumaş Dokusu:**
   - Kaynak kıyafette **derin pileler (pleats)** varsa, bunların sonuçta sönümlenerek düz/desensiz kumaşa dönüşmesi ürün kimliği kaybıdır.
5. **Özgün Tasarım Özellikleri:**
   - Ürünü benzerlerinden ayıran karakteristik dikiş, yaka, düğme, fermuar gibi ayırt edici öğeler korunmalıdır.

### Önemli: "Detay Yokluğu Kuralı"
- Eğer kaynak üründe bir aksesuar veya detay **fiilen bulunmuyorsa** (örneğin basic tişörtte kemer, toka, desen veya cep yoktur), bu detayın sonuçta aranması veya zorunlu tutulması **kesinlikle söz konusu değildir**. Yalnızca kaynak görselde var olan özellikler aranır.

---

## 3. Puanlama Skalası ve Metrikler

Her uygulanabilir metrik için `0` ile `4` arasında bir tamsayı puan veriniz:

| Puan | Anlamı | Tanım |
| :---: | :--- | :--- |
| **4** | Güçlü Koruma | Kaynak detaylar ve hedef anatomi hatasız, kusursuz aktarılmıştır. |
| **3** | Kabul Edilebilir | Küçük, kullanım gerçekçiliğini bozmayan minör kusurlar mevcuttur. |
| **2** | Belirgin Hata | Karakteristik detaylardan biri zayıflamış veya kaybolmuştur (Eşik altı). |
| **1** | Ağır Hata | Ürün kimliği, renk veya anatomi ciddi biçimde bozulmuştur. |
| **0** | Yanlış / Kullanılamaz | Yanlış ürün, tanınmaz form, ağır halüsinasyon veya çökme. |

### İncelenecek Metrikler:
1. `garment_identity`: Aynı gerçek ürün mü? Karakteristik detaylar (kemer, toka, pile vb.) korunmuş mu?
2. `color_pattern`: Renk ve desen doğruluğu (özgün siyahın korunması, ton sapması olmaması).
3. `cut`: Kesim, silüet, boy ve bedene döküm.
4. `fabric`: Kumaş dokusu, dikey pile derinliği ve yüzey karakteri.
5. `face`: Hedef kişinin yüzü, saçı ve kimlik korunumu.
6. `body`: Hedef kişinin vücut oranları ve ten özellikleri korunumu.
7. `arms_hands`: Kol, el ve parmak anatomisi (parmak sayısının ve boşlukların korunumu).
8. `source_pose`: Kaynak modelin pozundan/duruşundan taşınan yapay bozulma olmaması (4=hata yok).
9. `waist_belt_transition` *(Yalnızca etek kombinlerinde; üst giyim için `N/A`)*: Bel hattı birleşimi, kemer ve toka geçişi.
10. `footwear_ankle_transition` *(Yalnızca etek kombinlerinde; üst giyim için `N/A`)*: Bacak ten tonu, ayak bileği ve çıplak ayak geçişi.
11. `stage1_preservation` *(Yalnızca etek kombinlerinde; üst giyim için `N/A`)*: İki aşamalı akışta üst tişörtün etek eklenirken bozulmadan kalması.
12. `critical_failure` (`yes` / `no`): Yanlış ürün aktarımı, tanınamaz ürün veya ağır anatomik bozulma varsa `yes`.
13. `untargeted_changes` (`yes` / `no`): Seçilmeyen vücut uzuvlarının veya arka planın istenmeyen değişimi.

---

## 4. Karar Verme Kuralları (Verdict)

Her vaka için formdaki `overall_verdict` sütununa üç karardan birini yazınız:

- **`PASS` (Başarılı):**
  - Tüm uygulanabilir metrikler **en az 3** puan almışsa,
  - `critical_failure = no` ise,
  - `untargeted_changes = no` ise.
- **`FAIL` (Başarısız):**
  - Uygulanabilir metriklerden herhangi biri **3'ün altında (0, 1 veya 2)** kalmışsa, VEYA
  - `critical_failure = yes` ise (örneğin kemer/pile gibi ana detayların tamamen silinmesi, rengin bambaşka tona kayması), VEYA
  - `untargeted_changes = yes` ise.
- **`REVIEW` (İnceleme Gerekli):**
  - Görsel kanıt yetersizse, çözünürlük veya panel ölçeği nedeniyle detaydan emin olunamıyorsa **tahmin yürütmeyiniz**, `REVIEW` seçiniz ve `uncertainty_notes` sütununa belirsizliğin nedenini yazınız.

---

## 5. Değerlendirici Notları ve Gerekçelendirme

- Lütfen her vaka için `justification_notes` alanına kısa ve somut bir gerekçe yazınız (örneğin: *"Kemer detayı silinmiş, toka yok, pileler sönümlenmiş"* veya *"Tişört bedene doğal oturmuş, yaka temiz"*).
- Değerlendirme sırasında önceki yapay zekâ veya otomatik sistem puanları sizinle paylaşılmamıştır; lütfen yalnızca gördüğünüz piksel kanıtına dayanarak bağımsız karar veriniz.

---

## 6. Önemli Hatırlatma

Bu testte kullanılan görseller **sentetik teknik avatar provalarıdır**. Elde edilen sonuçlar sistemin temel görüntü işleme boru hattını denetlemek içindir; **gerçek insan bedenlerinde genellenebilirlik veya nihai ürün kalitesi kanıtı teşkil etmez**.

Katkılarınız için teşekkür ederiz.
