"""
Telegram Links Scraper Module - Telethon Version

This module uses Telethon to extract recent Telegram channel posts.
Requires authentication session to be set up first.
"""

import logging
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
import config


def normalize_telegram_channel(input_str: str) -> str:
    """
    Normalize Telegram channel input.
    
    Args:
        input_str: @username, t.me link, or plain username
    
    Returns:
        Normalized channel username (without @)
    """
    input_str = input_str.strip()
    
    if input_str.startswith("https://t.me/"):
        return input_str.replace("https://t.me/", "").strip("/")
    
    if input_str.startswith("@"):
        return input_str[1:]
    
    return input_str


async def _telegram_scraper_async(channel_input: str, max_posts: int = 5) -> list:
    """
    Async function to scrape Telegram channel posts.
    
    Args:
        channel_input: Channel username, @username, or t.me link
        max_posts: Maximum number of posts to retrieve (default: 5)
    
    Returns:
        List of Telegram post URLs
    """
    post_urls = []
    client = None
    
    try:
        # Normalize channel name
        channel = normalize_telegram_channel(channel_input)
        
        logging.info(f"Processing Telegram channel: @{channel}")
        
        # Create client with session
        client = TelegramClient(
            config.TELEGRAM_SESSION,
            config.TELEGRAM_API_ID,
            config.TELEGRAM_API_HASH
        )
        
        # Connect
        await client.start()
        logging.info("Connected to Telegram")
        
        # Try joining channel (safe if already joined)
        try:
            await client(JoinChannelRequest(channel))
        except Exception:
            pass  # Already joined or public channel
        
        # Get channel entity
        entity = await client.get_entity(channel)
        
        # Iterate through recent messages
        count = 0
        async for msg in client.iter_messages(entity, limit=max_posts):
            if msg.id:
                link = f"https://t.me/{channel}/{msg.id}"
                post_urls.append(link)
                logging.info(f"Found Telegram post: {link}")
                count += 1
        
        logging.info(f"Successfully collected {count} Telegram posts")
        
    except Exception as e:
        logging.error(f"Error processing Telegram channel {channel_input}: {e}")
        
    finally:
        if client:
            await client.disconnect()
    
    return post_urls


def telegram_scraper_recent(channel_input: str, max_posts: int = 5) -> list:
    """
    Scrape recent Telegram channel posts (sync wrapper).
    
    Args:
        channel_input: Channel username, @username, or t.me link
        max_posts: Maximum number of posts to retrieve (default: 5)
    
    Returns:
        List of Telegram post URLs
    """
    # Run async function in event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_telegram_scraper_async(channel_input, max_posts))
        loop.close()
        return result
    except Exception as e:
        logging.error(f"Error in Telegram scraper: {e}")
        return []

