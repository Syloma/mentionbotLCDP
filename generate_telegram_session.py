import asyncio
import os
import sys
from pathlib import Path
from getpass import getpass

from telethon import TelegramClient
from telethon.sessions import StringSession


def load_dotenv_file() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


async def main() -> None:
    load_dotenv_file()

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("TELEGRAM_API_ID ve TELEGRAM_API_HASH .env icinde bulunamadi.")
        api_id = api_id or input("TELEGRAM_API_ID: ").strip()
        api_hash = api_hash or getpass("TELEGRAM_API_HASH: ").strip()

    if not api_id or not api_hash:
        print("Hata: TELEGRAM_API_ID ve TELEGRAM_API_HASH gerekli.")
        sys.exit(1)

    client = TelegramClient(StringSession(), int(api_id), api_hash)
    await client.start()

    print("\nRailway Variables icin TELEGRAM_STRING_SESSION degeri:")
    print(client.session.save())
    print("\nBu degeri kimseyle paylasma. Telegram hesabina giris yetkisi verir.")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
