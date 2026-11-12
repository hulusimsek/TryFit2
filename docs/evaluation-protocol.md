# On ürünlük araştırma protokolü

Aynı hedef kişinin aynı fotoğrafı ve aynı başlangıç ayarları kullanılır: seed 42, 30 adım, guidance 1.5, tek örnek, model fotoğrafı, segmentation_free=true.

Hedef fotoğraf: tek yetişkin kişi, tam boy, yüz net, sade arka plan; kollar gövdeden ayrık ve bacaklar görünür. İlk kişide aşırı bol kıyafet yerine vücut yapısını okumaya izin veren gündelik kıyafet tercih edin. Bu başlangıç koşulu bir başarı garantisi değildir.

On kategori manifestte önceden tanımlıdır. Mankenli ürünlerde önden/çapraz/yan poz, el belde, saç örtmesi, açık ceket ve desen riskini `source_notes` alanına yazın. En az birkaç zor örneği koruyun; sadece kolay örnek seçerek başarı oranını artırmayın.

## Puanlar

Her boyut için 0 yanlış/kullanılamaz; 1 ağır hata; 2 belirgin hata; 3 küçük hata ile kabul edilebilir; 4 güçlü koruma.

| CSV alanı | İncelenecek özellik |
|---|---|
| garment_identity | Aynı gerçek ürün mü? Cep, yaka, düğme, fermuar ve detaylar |
| color_pattern | Renk, logo ve desen yerleşimi |
| cut | Kesim, boy, hacim ve siluet |
| face | Hedef kişinin yüzü, kimliği ve saçı |
| body | Vücut oranları ve ten özellikleri |
| arms_hands | Kol, el, parmak anatomisi ve örtüşmeler |
| fabric | Kumaş dokusu, kırışıklık ve ışık |
| source_pose | Kaynak pozundan/kaynak kişiden taşınan hatalar; 4 hata yok, 0 ağır hata |

`critical_failure=yes`: yanlış ürün, belirgin yüz/kimlik değişimi veya anatomi bozulması. Diğer durumlarda `no`. `reviewer` ve `notes` doldurun; hatanın yerini ve nedenini yazın. Boş skorlar, eksik değerlendirici ve geçersiz değerler başarı sayılmaz.

### Zorunlu Kalite Kabul Kriteri: Kaynak Ürün Kimliğinin ve Karakteristik Detaylarının Korunması (Karar D15)

Bir virtual try-on sonucu yalnızca kıyafet kategorisi veya genel rengi doğru olduğu için başarılı kabul edilemez. Kaynak kıyafette fiilen bulunan karakteristik tasarım özellikleri korunmalıdır:

- **Renk ve Desen:** Kaynak ürünün özgün rengi ve deseni korunmalıdır (`color_pattern >= 3`). Rengin belirgin şekilde yabancılaşması (örneğin siyah ürünün bronz/kahverengiye kayması) ürün kimliği ihlalidir.
- **Kesim ve Silüet:** Kıyafetin boyu, formu ve kalıbı korunmalıdır (`cut >= 3`).
- **Kemer ve Toka Gibi Aksesuar Detayları:** Kaynak üründe belirgin bir kemer, metal toka veya özel bir bel bandı varsa, bunların sonuçta kaybolması veya detaysız sıradan bir bel çizgisine dönüşmesi kalite kabul kriterinin ihlalidir (`waist_belt_transition >= 3`, `garment_identity >= 3`).
- **Pileler ve Karakteristik Kumaş Dokusu:** Kaynak üründe derin pileler veya özgün kumaş dokusu varsa, bunların sönümlenerek düz/desensiz kumaşa dönüşmesi kabul edilmez (`fabric >= 3`, `garment_identity >= 3`).
- **Özgün Tasarım Özellikleri:** Ürünü diğer benzer kıyafetlerden ayıran karakteristik dikiş, yaka, düğme, fermuar ve detaylar korunmalıdır.

**Koşullar ve Sınırlar:**
- **Detay Yokluğu Kuralı:** Kemer, toka, pile, cep gibi detaylar kaynak üründe fiilen bulunmuyorsa, bunların sonuçta aranması veya zorunlu tutulması söz konusu değildir. Değerlendirme yalnızca kaynak görselde mevcut özellikler üzerinden yapılır.
- **Kritik Hata Gerekçesi:** Kaynak üründe belirgin olan kemer, toka veya derin pilelerin tamamen yok olması ya da bambaşka bir tasarıma dönüşmesi `garment_identity` puanını 3'ün altına düşürür; ürünün tanınamaz hale geldiği veya bambaşka bir ürün izlenimi verdiği durumlarda `critical_failure=yes` tetiklenir.
- **Geçmiş Koşuların Durumu:** Bu karar mevcut/geçmiş GPU pilot sonuçlarını geriye dönük olarak otomatik değiştirmez; arşivlenmiş teknik pilot kayıtları (`runs/*`) olduğu gibi korunur. Ancak mevcut ve yeni sonuçlar bu kalite kabul kriteri çerçevesinde bağımsız değerlendiriciler tarafından değerlendirilir.

Kombin bütünlüğü için ayrıca `untargeted_changes=yes/no` kaydedilir: seçilmeyen kıyafetin kısalması, kaynak ayakkabı/kolye/iç üstün de taşınması gibi değişiklikler `yes` olur ve örneği başarısız yapar. Bu alan vücut şekli puanından ayrıdır. Yeni CSV'de boş bırakılırsa değerlendirme tamamlanmış sayılmaz; eski CSV şemalarında alan bulunmayabilir. İlk 10 ürünlük rapor sekiz puana ek olarak bu daha sıkı kombin koruma kontrolünü içerir; oran bu rubriğe bağlı görsel ön değerlendirmedir.

Tek örneğin geçmesi: sekiz puanın tamamı >=3 ve kritik hata yok. Önerilen araştırma kapısı: on örneğin en az sekizi geçmeli. Üretilmeyen örnekler onluk paydaya dahildir. Tek ürün denemesi kapıyı geçiremez. Henüz puanlanmayan üretilmiş örnekler varsa kapı `pending` kalır.

Başarısızlıklar ve ilk çıktılar silinmez. Yeni seed/adım/maskeleme ayrı run oluşturur. İlk ayarlı 10'luk sonuç ile ayar araması sonrası en iyi sonuç ayrı raporlanır; seed seçerek ilk başarı oranı değiştirilmez.

`completed` yalnızca model çıktı verdi demektir. İnsan değerlendirmesi `quality.json` içindedir. OOM sonrası kalan örnekler `not_run`, başlatma hataları `setup_failed` olur. PNG, hash, manifest, ortam sürümleri, traceback, süre ve PyTorch peak allocated/reserved VRAM kaydedilir. Bu VRAM sayıları tüm sürücü/ONNX belleğini kapsamaz; toplam kullanım için nvidia-smi ayrıca incelenir.

Tek kişinin on fotoğraf aktarımı fizibilite denemesidir. Genel kullanıcı başarısı, gerçek beden uyumu, gerçek kumaş fiziği veya ürünün görünmeyen ayrıntılarının doğruluğunu kanıtlamaz. Sonraki aşama farklı vücut tipleri ve hedef pozlarla tekrar testtir.
