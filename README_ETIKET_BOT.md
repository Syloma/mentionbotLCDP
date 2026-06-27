# Telegram Etiketleme Botu

Bu bot Telethon ile calisir ve gruptaki uyeleri parca parca etiketler. Normal Telegram Bot API her zaman tum grup uyelerini listeleyemedigi icin bu dosya userbot mantigiyla calisir.

## Kurulum

1. `https://my.telegram.org` adresinden `api_id` ve `api_hash` al.
2. Ornek env dosyasini kopyala:

```powershell
Copy-Item mentionbot.env.example .env
```

3. `.env` icindeki degerleri doldur:

```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=buraya_api_hash_yaz
```

4. Gerekirse bagimliligi yukle:

```powershell
pip install -r requirements.txt
```

5. Botu baslat:

```powershell
python telegram_etiket_bot.py
```

Ilk calistirmada telefon numarani ve Telegram dogrulama kodunu ister. Oturum `data/etiketbot.session` olarak kaydedilir.

## Komutlar

Grupta su komutlari kullanabilirsin:

```text
/etiket Mesaj metni
/tag Mesaj metni
/iptal
/yardim
```

Ornek:

```text
/etiket Turnuva 10 dakika sonra basliyor.
```

## Ayarlar

`.env` icinden degistirilebilir:

- `MENTIONS_PER_MESSAGE`: Tek mesajda kac kisi etiketlenecek.
- `MESSAGE_DELAY_SECONDS`: Mesajlar arasi bekleme suresi.
- `ADMIN_ONLY`: `1` ise sadece grup yoneticileri kullanir, `0` ise herkes kullanabilir.

Telegram limitlerine takilmamak icin cok buyuk gruplarda `MENTIONS_PER_MESSAGE` degerini dusuk, `MESSAGE_DELAY_SECONDS` degerini daha yuksek tut.

## Railway Deploy

Railway'de surekli calismasi icin bu repoda `Procfile`, `railway.json` ve `runtime.txt` hazir.

1. Lokalde `.env` icine `TELEGRAM_API_ID` ve `TELEGRAM_API_HASH` yaz.
2. Lokalde oturum string'i uret:

```powershell
python generate_telegram_session.py
```

3. Cikan uzun degeri Railway projesinde `Variables` bolumune ekle:

```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=buraya_api_hash_yaz
TELEGRAM_STRING_SESSION=cikan_uzun_session_degeri
MENTIONS_PER_MESSAGE=5
MESSAGE_DELAY_SECONDS=2.0
ADMIN_ONLY=1
```

4. Railway'de GitHub repo ile deploy et veya Railway CLI kullan.

Railway servis tipi worker olarak calisir; web portu acmasina gerek yok. `TELEGRAM_STRING_SESSION` degerini kimseyle paylasma, Telegram hesabina giris yetkisi verir.
