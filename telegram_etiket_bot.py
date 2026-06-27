import asyncio
import html
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import ChannelParticipantsAdmins, User


DATA_DIR = Path("data")
SESSION_NAME = os.getenv("TELEGRAM_SESSION", str(DATA_DIR / "etiketbot"))
STRING_SESSION = os.getenv("TELEGRAM_STRING_SESSION")
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

MENTIONS_PER_MESSAGE = int(os.getenv("MENTIONS_PER_MESSAGE", "5"))
MESSAGE_DELAY_SECONDS = float(os.getenv("MESSAGE_DELAY_SECONDS", "2.0"))
ADMIN_ONLY = os.getenv("ADMIN_ONLY", "1").lower() not in {"0", "false", "hayir", "hayır", "no"}

TAG_COMMANDS = ("/tag", "!tag", ".tag", "/etiket", "!etiket", ".etiket")
CANCEL_COMMANDS = ("/cancel", "!cancel", ".cancel", "/iptal", "!iptal", ".iptal")
HELP_COMMANDS = ("/help", "!help", ".help", "/yardim", "/yardım", "!yardim", "!yardım")

active_jobs: dict[int, asyncio.Task] = {}


@dataclass(frozen=True)
class MentionTarget:
    user_id: int
    display_name: str


def require_config() -> tuple[int, str]:
    if not API_ID or not API_HASH:
        print("Hata: TELEGRAM_API_ID ve TELEGRAM_API_HASH ortam degiskenleri ayarlanmali.")
        print("Ornek: copy mentionbot.env.example .env ve README_ETIKET_BOT.md dosyasina bak.")
        sys.exit(1)

    try:
        return int(API_ID), API_HASH
    except ValueError:
        print("Hata: TELEGRAM_API_ID sayisal olmali.")
        sys.exit(1)


def load_dotenv_file() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def first_command_match(text: str, commands: tuple[str, ...]) -> str | None:
    lowered = text.casefold()
    for command in commands:
        if lowered == command or lowered.startswith(command + " "):
            return command
    return None


def command_argument(text: str, command: str) -> str:
    return text[len(command):].strip()


def user_display_name(user: User) -> str:
    full_name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
    return full_name or user.username or f"Kullanici {user.id}"


def mention_html(target: MentionTarget) -> str:
    return f'<a href="tg://user?id={target.user_id}">{html.escape(target.display_name)}</a>'


async def sender_is_admin(client: TelegramClient, chat_id: int, sender_id: int) -> bool:
    if not ADMIN_ONLY:
        return True

    async for admin in client.iter_participants(chat_id, filter=ChannelParticipantsAdmins):
        if admin.id == sender_id:
            return True
    return False


async def collect_targets(client: TelegramClient, chat_id: int) -> list[MentionTarget]:
    targets: list[MentionTarget] = []

    async for user in client.iter_participants(chat_id, aggressive=True):
        if user.bot or user.deleted:
            continue
        targets.append(MentionTarget(user.id, user_display_name(user)))

    return targets


async def tag_members(event: events.NewMessage.Event, custom_text: str) -> None:
    chat_id = event.chat_id
    client = event.client
    sender = await event.get_sender()

    if not await sender_is_admin(client, chat_id, sender.id):
        await event.reply("Bu komutu sadece grup yoneticileri kullanabilir.")
        return

    if chat_id in active_jobs and not active_jobs[chat_id].done():
        await event.reply("Bu grupta zaten etiketleme calisiyor. Durdurmak icin /iptal yaz.")
        return

    async def worker() -> None:
        targets = await collect_targets(client, chat_id)
        if not targets:
            await event.reply("Etiketlenecek uygun uye bulunamadi.")
            return

        header = custom_text or "Herkes buraya bakabilir mi?"
        await event.reply(f"Etiketleme basladi. {len(targets)} uye parcalar halinde etiketlenecek.")

        for index in range(0, len(targets), MENTIONS_PER_MESSAGE):
            batch = targets[index:index + MENTIONS_PER_MESSAGE]
            mention_line = " ".join(mention_html(target) for target in batch)
            text = f"{html.escape(header)}\n\n{mention_line}"

            try:
                await client.send_message(chat_id, text, parse_mode="html", link_preview=False)
            except FloodWaitError as exc:
                await asyncio.sleep(exc.seconds + 1)
                await client.send_message(chat_id, text, parse_mode="html", link_preview=False)

            await asyncio.sleep(MESSAGE_DELAY_SECONDS)

        await event.reply("Etiketleme tamamlandi.")

    task = asyncio.create_task(worker())
    active_jobs[chat_id] = task

    try:
        await task
    except asyncio.CancelledError:
        await event.reply("Etiketleme iptal edildi.")
    finally:
        active_jobs.pop(chat_id, None)


async def cancel_tagging(event: events.NewMessage.Event) -> None:
    task = active_jobs.get(event.chat_id)
    if not task or task.done():
        await event.reply("Bu grupta aktif etiketleme yok.")
        return

    sender = await event.get_sender()
    if not await sender_is_admin(event.client, event.chat_id, sender.id):
        await event.reply("Bu komutu sadece grup yoneticileri kullanabilir.")
        return

    task.cancel()


def help_text() -> str:
    return (
        "Etiket bot komutlari:\n"
        "/etiket Mesaj - gruptaki uyeleri parca parca etiketler\n"
        "/tag Mesaj - ayni komutun kisa hali\n"
        "/iptal - aktif etiketlemeyi durdurur\n\n"
        "Not: Varsayilan olarak sadece grup yoneticileri kullanabilir."
    )


async def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    load_dotenv_file()

    global API_ID, API_HASH
    API_ID = os.getenv("TELEGRAM_API_ID")
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    api_id, api_hash = require_config()

    session = StringSession(STRING_SESSION) if STRING_SESSION else SESSION_NAME
    client = TelegramClient(session, api_id, api_hash)

    @client.on(events.NewMessage(incoming=True))
    async def handler(event: events.NewMessage.Event) -> None:
        if not event.is_group:
            return

        text = (event.raw_text or "").strip()
        if not text:
            return

        command = first_command_match(text, HELP_COMMANDS)
        if command:
            await event.reply(help_text())
            return

        command = first_command_match(text, CANCEL_COMMANDS)
        if command:
            await cancel_tagging(event)
            return

        command = first_command_match(text, TAG_COMMANDS)
        if command:
            await tag_members(event, command_argument(text, command))

    print("Etiket bot aktif. Cikmak icin Ctrl+C.")
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot kapatildi.")
