"""
Telegram Authentication Setup Script

Run this script ONCE to authenticate and create a session file.
The session will be reused by the main application.
"""

import asyncio
from telethon import TelegramClient
import config

async def setup_telegram():
    """Interactive setup for Telegram authentication"""
    print("=" * 60)
    print("TELEGRAM AUTHENTICATION SETUP")
    print("=" * 60)
    print()
    print(f"API ID: {config.TELEGRAM_API_ID}")
    print(f"API Hash: {config.TELEGRAM_API_HASH}")
    print(f"Session file: {config.TELEGRAM_SESSION}")
    print()
    print("You will be prompted to enter:")
    print("1. Your phone number (with country code, e.g., +1234567890)")
    print("2. Verification code (sent to your Telegram app)")
    print("3. 2FA password (if you have one enabled)")
    print()
    print("-" * 60)
    print()
    
    # Create client
    client = TelegramClient(
        config.TELEGRAM_SESSION,
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH
    )
    
    try:
        # Start client (this will prompt for phone/code if needed)
        await client.start()
        
        # Get current user info
        me = await client.get_me()
        
        print()
        print("=" * 60)
        print("✅ AUTHENTICATION SUCCESSFUL!")
        print("=" * 60)
        print()
        print(f"Logged in as: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}")
        print(f"Phone: {me.phone}")
        print()
        print(f"Session saved to: {config.TELEGRAM_SESSION}.session")
        print()
        print("You can now use Telegram scraping in the main application!")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ AUTHENTICATION FAILED")
        print("=" * 60)
        print()
        print(f"Error: {e}")
        print()
        print("Please try again and make sure:")
        print("- Your phone number is correct (include country code)")
        print("- You enter the verification code from Telegram app")
        print("- Your 2FA password is correct (if enabled)")
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    print()
    asyncio.run(setup_telegram())
    print()

