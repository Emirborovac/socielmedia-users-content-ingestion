"""
YouTube Links Scraper Module - yt-dlp Version (Based on sample)

This module uses yt-dlp to extract recent YouTube videos or shorts.
Supports @handles, channel IDs, and custom channel names.
"""

import logging
from yt_dlp import YoutubeDL
import config


def normalize_youtube_url(channel_input: str, content_type: str) -> str:
    """
    Normalize YouTube channel input to full URL with content type.
    
    Args:
        channel_input: @handle, channel ID (UCxxxx), custom name, or full URL
        content_type: 'videos' or 'shorts'
    
    Returns:
        Full YouTube URL with content type path
    """
    channel_input = channel_input.strip()

    # Already a full URL
    if channel_input.startswith("http"):
        if f"/{content_type}" not in channel_input:
            return channel_input.rstrip("/") + f"/{content_type}"
        return channel_input

    # @handle
    if channel_input.startswith("@"):
        return f"https://www.youtube.com/{channel_input}/{content_type}"

    # Channel ID (UCxxxx)
    if channel_input.startswith("UC"):
        return f"https://www.youtube.com/channel/{channel_input}/{content_type}"

    # Custom channel name
    return f"https://www.youtube.com/c/{channel_input}/{content_type}"


def youtube_scraper_recent_ytdlp(account_url: str, content_type: str = "shorts", max_posts: int = 5) -> list:
    """
    Scrape recent YouTube videos or shorts using yt-dlp.
    
    Args:
        account_url: YouTube channel URL, @handle, or channel ID
        content_type: 'videos' or 'shorts' (default: 'shorts')
        max_posts: Maximum number of posts to retrieve (default: 5)
    
    Returns:
        List of YouTube video URLs
    """
    video_urls = []
    
    try:
        # Normalize URL
        url = normalize_youtube_url(account_url, content_type)
        
        logging.info(f"Processing YouTube channel: {url}")
        logging.info(f"Content type: {content_type}")
        
        # yt-dlp configuration
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,  # Only metadata, no video download
            'no_warnings': True,
            'ignoreerrors': True,
        }
        
        # Add proxy if configured
        if config.PROXY:
            ydl_opts['proxy'] = config.PROXY
            logging.info("Using proxy for YouTube scraping")
        
        # Extract info
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        if not info:
            logging.error("No info returned from yt-dlp")
            return video_urls
        
        # Get entries
        entries = info.get("entries") or []
        
        if not entries:
            logging.warning(f"No {content_type} found for this channel")
            return video_urls
        
        # Take first N entries (YouTube sorts newest → oldest)
        recent = entries[:max_posts]
        
        for entry in recent:
            if not entry:
                continue
            
            # Build video URL
            video_url = None
            if "url" in entry and entry["url"]:
                video_url = entry["url"]
            elif "id" in entry:
                video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            
            if video_url and video_url not in video_urls:
                video_urls.append(video_url)
                title = entry.get('title', 'Unknown')[:50]
                logging.info(f"Found YouTube {content_type}: {title}...")
        
        logging.info(f"Successfully collected {len(video_urls)} YouTube {content_type}")
        
    except Exception as e:
        logging.error(f"Error processing YouTube channel {account_url}: {e}")
    
    return video_urls


