import asyncio
import re
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest

API_ID = 31485887
API_HASH = "92bff248d4fbcf62e4f9b4af924ebf3c"
SESSION = "tg_recent_posts"

def normalize_channel(input_str: str) -> str:
    input_str = input_str.strip()
    if input_str.startswith("https://t.me/"):
        return input_str.replace("https://t.me/", "").strip("/")
    if input_str.startswith("@"):
        return input_str[1:]
    return input_str

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    channel_input = input("Enter channel username or t.me link: ")
    channel = normalize_channel(channel_input)

    # Try joining channel (safe if already joined)
    try:
        await client(JoinChannelRequest(channel))
    except Exception:
        pass  # already joined or public channel

    entity = await client.get_entity(channel)

    print("\nRecent 5 post links:\n")

    count = 0
    async for msg in client.iter_messages(entity, limit=5):
        if msg.id:
            link = f"https://t.me/{channel}/{msg.id}"
            print(link)
            count += 1

    if count == 0:
        print("No posts found.")

    await client.disconnect()

asyncio.run(main())
