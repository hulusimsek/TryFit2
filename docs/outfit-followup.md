# Kombin deneyinin ikinci turu

## Yapılan değişiklik

Aynı Trendyol ürününün galerisinden mankenli kaynak görseller bulundu ve indirildi. Kaynak URL'ler `data/first-outfit/gallery/sources.json` içinde saklandı. [Ürün sayfası](https://www.trendyol.com/uyguntarz/unisex-yumusak-dokulu-duz-3-iplik-oversize-sweatshirt-sade-ve-modern-gorunum-p-1025061091).

`runs/source-comparison-9949970f/` altında aynı hedef ve ayarlarla iki mankenli kaynak ve temiz flat-lay fotoğrafı karşılaştırıldı. Mankenli kaynakla yaka iyileşti, ancak üst sonradan giydirildiğinde üst kıyafet kısa kaldı. Temiz flat-lay yine yanlış V yaka üretti. Bu, tüm mankenli görsellerin daha iyi olduğu anlamına gelmez; aynı ürünün bu kaynaklarında gözlendi.

`runs/protected-outfit-d24e679a/` altında farklı yöntem denendi:

1. Başlangıç mankenine, galerideki `gallery-4.jpg` mankenli kaynak kullanılarak üst aktarıldı.
2. Bu görüntüye kullanıcının pijama altı fotoğrafından alt aktarıldı.
3. İlk üst aktarımındaki üst kıyafet/yüz/saç/kol/el maskesi çıkarıldı. İkinci çıktıdaki bu bölgeler ilk görüntüden korundu; kenarda 3×3 yumuşatma uygulandı. Alt kıyafet ikinci model çıktısından geliyor.

Bu son adım açık bir görüntü birleştirme işlemidir; ham model çıktısı gibi sunulmaz. Her iki kıyafet önce FASHN ile hedef kişiye aktarılmıştır. Kaynak kişinin gövdesi veya hazır kıyafet posteri hedefin üstüne yapıştırılmadı. Ham ve korumalı çıktılar ayrı saklandı.

## Gözlenen sonuç

Kanguru cep, üst etek ucu ve yaka ilk denemeye göre daha iyi korunuyor; iki parça aynı mankende birlikte görülebiliyor. İlk sonuçtaki belirgin bluz/V yaka görünümü azaldı. Bununla birlikte kapüşon hacmi, oversize kesim ve birebir ürün detayları hâlâ tam doğrulanmış değil. Boy/kilo, ölçülü 3D beden üretimi değil sentetik görsel profil olarak kalıyor.

Yüz/saç ve üst kıyafet korunmuş iç piksellerinde ilk görüntüye fark sıfır; maskeden uzak bölgelerde ikinci görüntüye fark sıfır olarak gerçek çıktı üzerinde kontrol edildi. Sayılar `run.json/preservation_checks` içinde. Bu kontrol görsel kalite veya beden doğruluğu puanı değildir.

22 yerel kontrol geçti. Tek örnek, on ürünlük kalite kapısı veya genel kullanıcı başarısı kanıtı değildir. Henüz backend/arayüz aşamasına geçilmedi.

## Yeniden çalıştırma

```powershell
.\.venv\Scripts\python.exe ai-worker/app/compare_sources.py --parent runs/outfit-20261110T001523Z-3b4bfe
.\.venv\Scripts\python.exe ai-worker/app/protect_outfit.py
```

Komutlar yeni run klasörleri oluşturur. Maskeli koruma değişen pozlarda hizalama hatası, kenar izi ve hatalı parser etiketi oluşturabilir; farklı ürün/pozlarla test edilmelidir. Sonraki araştırma: bu yöntemin farklı ürünlerde tekrarı ve oversize/uzun üst kesiminin daha iyi korunması.
