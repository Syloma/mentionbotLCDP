import asyncio
import html
import os
import sys
import traceback

from telethon import TelegramClient, events
from telethon.errors import ChatAdminRequiredError, FloodWaitError, RPCError
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator


API_ID = os.getenv("TELEGRAM_API_ID") or os.getenv("APP_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH") or os.getenv("API_HASH") or os.getenv("APP_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TOKEN")

MENTIONS_PER_MESSAGE = int(os.getenv("MENTIONS_PER_MESSAGE", "5"))
MESSAGE_DELAY_SECONDS = float(os.getenv("MESSAGE_DELAY_SECONDS", "2.0"))

# Sen herkes kullansin istedigin icin varsayilan kapali.
ADMIN_ONLY = os.getenv("ADMIN_ONLY", "0").lower() in {"1", "true", "evet", "yes"}

MENTION_COMMANDS = ("/mentionall", "/all", "/etiket", "/tag")
CANCEL_COMMANDS = ("/cancel", "/iptal")
HELP_COMMANDS = ("/help", "/yardim", "/yardım", "/start")

active_jobs: dict[int, asyncio.Task] = {}


def require_config() -> tuple[int, str, str]:
    missing = []
    if not API_ID:
        missing.append("TELEGRAM_API_ID")
    if not API_HASH:
        missing.append("TELEGRAM_API_HASH")
    if not BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")

    if missing:
        print("Eksik ortam degiskenleri: " + ", ".join(missing))
        print("Railway Variables icine API bilgilerini ve BotFather tokenini ekle.")
        sys.exit(1)

    try:
        return int(API_ID), API_HASH, BOT_TOKEN
    except ValueError:
        print("TELEGRAM_API_ID sayisal olmali.")
        sys.exit(1)


def command_match(
    text: str,
    commands: tuple[str, ...],
    bot_username: str | None = None,
) -> tuple[str, str] | None:
    """Komutu, gruplarda Telegram'in ekledigi /komut@bot biçimiyle de eşleştir."""
    parts = text.split(maxsplit=1)
    command_token = parts[0].casefold()
    argument = parts[1].strip() if len(parts) == 2 else ""

    command_name, separator, target_username = command_token.partition("@")
    if separator:
        if not bot_username or target_username != bot_username.lstrip("@").casefold():
            return None

    for command in commands:
        if command_name == command.casefold():
            return command, argument
    return None


def mention_user(user) -> str:
    name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
    name = name or user.username or f"Kullanici {user.id}"
    return f'<a href="tg://user?id={user.id}">{html.escape(name)}</a>'


async def sender_is_admin(client: TelegramClient, chat_id: int, sender_id: int) -> bool:
    participant = await client(GetParticipantRequest(chat_id, sender_id))
    return isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))


async def can_use_command(event: events.NewMessage.Event) -> bool:
    if not ADMIN_ONLY:
        return True

    try:
        return await sender_is_admin(event.client, event.chat_id, event.sender_id)
    except Exception:
        return False


def help_text() -> str:
    return (
        "MentionAll Bot komutlari:\n\n"
        "/mentionall mesaj - gruptaki uyeleri etiketler\n"
        "/etiket mesaj - Turkce komut\n"
        "/tag mesaj - kisa komut\n"
        "/iptal veya /cancel - aktif etiketlemeyi durdurur\n\n"
        "Bir mesaja yanit vererek /mentionall yazarsan, etiketler o mesaja yanit olarak gider."
    )


async def run_mention_job(event: events.NewMessage.Event, message_text: str) -> None:
    chat_id = event.chat_id
    client = event.client
    reply_message = await event.get_reply_message() if event.is_reply else None

    async def worker() -> None:
        count = 0
        buffer: list[str] = []

        await event.reply("Etiketleme basladi. Durdurmak icin /iptal yaz.")

        async for user in client.iter_participants(chat_id):
            if user.bot or user.deleted:
                continue

            buffer.append(mention_user(user))
            count += 1

            if len(buffer) >= MENTIONS_PER_MESSAGE:
                await send_mentions(client, chat_id, buffer, message_text, reply_message)
                buffer.clear()
                await asyncio.sleep(MESSAGE_DELAY_SECONDS)

        if buffer:
            await send_mentions(client, chat_id, buffer, message_text, reply_message)

        await event.reply(f"Etiketleme tamamlandi. {count} uye etiketlendi.")

    task = asyncio.create_task(worker())
    active_jobs[chat_id] = task

    try:
        await task
    except asyncio.CancelledError:
        await event.reply("Etiketleme iptal edildi.")
    except ChatAdminRequiredError:
        await event.reply(
            "Uye listesini alamadim. Buyuk gruplarda botu yonetici yapip "
            "yeniden dene (uye listesini gorme yetkisi gerekli)."
        )
    except RPCError as exc:
        print(f"Telegram API hatasi ({chat_id}): {type(exc).__name__}: {exc}")
        await event.reply(
            "Telegram uye listesini vermedi. Botun grupta yonetici oldugunu "
            "kontrol edip yeniden dene."
        )
    except Exception:
        print(f"Etiketleme hatasi ({chat_id}):")
        traceback.print_exc()
        await event.reply("Etiketleme beklenmeyen bir hata nedeniyle durdu. Lutfen yeniden dene.")
    finally:
        active_jobs.pop(chat_id, None)


async def send_mentions(client, chat_id: int, mentions: list[str], message_text: str, reply_message) -> None:
    mention_line = " ".join(mentions)
    if reply_message:
        text = mention_line
        send = lambda: reply_message.reply(text, parse_mode="html", link_preview=False)
    else:
        text = f"{mention_line}\n\n{html.escape(message_text)}" if message_text else mention_line
        send = lambda: client.send_message(chat_id, text, parse_mode="html", link_preview=False)

    while True:
        try:
            await send()
            return
        except FloodWaitError as exc:
            # Kalabalik gruplarda arka arkaya birden fazla FloodWait gelebilir.
            await asyncio.sleep(exc.seconds + 1)


async def handle_mention(event: events.NewMessage.Event, message_text: str) -> None:
    if event.is_private:
        await event.reply("Bu komut grup ve kanallarda kullanilir.")
        return

    if not await can_use_command(event):
        await event.reply("Bu komutu sadece grup yoneticileri kullanabilir.")
        return

    if active_jobs.get(event.chat_id):
        await event.reply("Bu grupta etiketleme zaten calisiyor. Durdurmak icin /iptal yaz.")
        return

    await run_mention_job(event, message_text)


async def handle_cancel(event: events.NewMessage.Event) -> None:
    task = active_jobs.get(event.chat_id)
    if not task or task.done():
        await event.reply("Aktif etiketleme yok.")
        return

    task.cancel()


async def main() -> None:
    api_id, api_hash, bot_token = require_config()
    client = TelegramClient("mentionall_bot", api_id, api_hash)

    await client.start(bot_token=bot_token)
    me = await client.get_me()
    bot_username = (me.username or "").casefold()

    @client.on(events.NewMessage(incoming=True))
    async def handler(event: events.NewMessage.Event) -> None:
        text = (event.raw_text or "").strip()
        if not text:
            return

        if command_match(text, HELP_COMMANDS, bot_username):
            await event.reply(help_text())
            return

        cancel = command_match(text, CANCEL_COMMANDS, bot_username)
        if cancel:
            await handle_cancel(event)
            return

        mention = command_match(text, MENTION_COMMANDS, bot_username)
        if mention:
            await handle_mention(event, mention[1])

    print("MentionAll bot aktif.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot kapatildi.")
