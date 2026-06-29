# MentionAll Telegram Bot

Bu bot BotFather token'i ile calisir. Telefon numarasi veya user session gerekmez.

## Railway Variables

Railway projesinde `Variables` bolumune sunlari ekle:

```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=buraya_api_hash_yaz
TELEGRAM_BOT_TOKEN=botfather_token_buraya
MENTIONS_PER_MESSAGE=5
MESSAGE_DELAY_SECONDS=2.0
ADMIN_ONLY=0
```

Eski MentionAll botlarindaki isimleri de destekler:

```env
APP_ID=123456
API_HASH=buraya_api_hash_yaz
TOKEN=botfather_token_buraya
```

## BotFather

1. Telegram'da `@BotFather` hesabina gir.
2. `/newbot` yaz.
3. Bot adi ve kullanici adi belirle.
4. Verdigi token'i Railway'de `TELEGRAM_BOT_TOKEN` olarak ekle.

## Komutlar

Grupta herkes kullanabilir:

```text
/mentionall mesaj
/etiket mesaj
/tag mesaj
/iptal
/cancel
/yardim
```

Gruplarda Telegram'in ekledigi `/etiket@BotKullaniciAdi` biçimi de desteklenir.

Bir mesaja yanit verip `/mentionall` yazarsan, bot etiketleri o mesaja yanit olarak yollar.

## Notlar

- Botu gruba eklemen gerekir.
- Buyuk gruplar Telegram'da `megagroup` sayilir. Bot uye listesini alamiyorsa botu grup
  yoneticisi yapip yeniden dene.
- `ADMIN_ONLY=1` yaparsan komutlari sadece grup yoneticileri kullanabilir.
- Cok buyuk gruplarda Telegram limitlerine takilmamak icin `MENTIONS_PER_MESSAGE` dusuk, `MESSAGE_DELAY_SECONDS` daha yuksek tutulmali.
