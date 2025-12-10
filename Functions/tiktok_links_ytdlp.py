"""
TikTok Links Scraper Module - yt-dlp Version

This module uses yt-dlp to extract recent TikTok posts.
Much faster and more reliable than browser-based scraping.
"""

import logging
from yt_dlp import YoutubeDL
import config


def tiktok_scraper_recent_ytdlp(account_url: str, max_posts: int = 5) -> list:
    """
    Scrape recent TikTok posts using yt-dlp.
    
    Args:
        account_url: TikTok account URL (e.g., https://www.tiktok.com/@username)
        max_posts: Maximum number of posts to retrieve (default 5)
    
    Returns:
        List of TikTok post URLs
    """
    video_urls = []
    
    try:
        # Extract username from URL
        if '@' in account_url:
            username = account_url.split('@')[-1].split('/')[0].split('?')[0]
        else:
            username = account_url.split('tiktok.com/')[-1].split('/')[0].split('?')[0]
            if not username.startswith('@'):
                username = f"@{username}"
        
        logging.info(f"Processing TikTok account: @{username}")
        
        # yt-dlp configuration
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # Don't download videos, just extract info
            'skip_download': True,
            'no_warnings': True,
            'ignoreerrors': True,  # Continue on errors
            'playlistend': max_posts,  # Limit to N posts
        }
        
        # Add proxy if configured
        if config.PROXY:
            ydl_opts['proxy'] = config.PROXY
            logging.info("Using proxy for TikTok scraping")
        
        # Ensure URL format is correct
        url = f"https://www.tiktok.com/@{username.lstrip('@')}"
        
        logging.info(f"Extracting posts from: {url}")
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logging.error("No info returned from yt-dlp")
                return video_urls
            
            if 'entries' not in info:
                logging.error("No posts found. User may be private or not exist.")
                return video_urls
            
            # Extract URLs from entries
            posts = info['entries'][:max_posts]
            
            for entry in posts:
                if entry:
                    # Try different URL fields
                    video_url = None
                    if 'url' in entry:
                        video_url = entry['url']
                    elif 'webpage_url' in entry:
                        video_url = entry['webpage_url']
                    elif 'id' in entry:
                        video_url = f"https://www.tiktok.com/@{username.lstrip('@')}/video/{entry['id']}"
                    
                    if video_url and video_url not in video_urls:
                        video_urls.append(video_url)
                        title = entry.get('title', 'Unknown')[:50]
                        logging.info(f"Found TikTok post: {title}...")
        
        logging.info(f"Successfully collected {len(video_urls)} TikTok posts")
        
    except Exception as e:
        logging.error(f"Error processing TikTok account {account_url}: {e}")
    
    return video_urls

