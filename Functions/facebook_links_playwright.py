"""
Facebook Links Scraper - Playwright Version

Extracts recent post links from Facebook pages.
Supports photos, videos, stories, and any post type.
"""

import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import config
import time


def facebook_scraper_recent_playwright(account_url: str, cookie_file: str = None, max_posts: int = 5) -> list:
    """
    Scrape recent Facebook posts using Playwright.
    
    Args:
        account_url: Facebook page URL (e.g., https://web.facebook.com/aljazeera)
        cookie_file: Path to cookie file (optional)
        max_posts: Maximum number of posts to retrieve (default: 5)
    
    Returns:
        List of post URLs
    """
    post_links = []
    
    with sync_playwright() as p:
        try:
            # Launch browser
            browser = p.chromium.launch(
                headless=config.HEADLESS_MODE,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            logging.info(f"Navigating to Facebook page: {account_url}")
            
            # Navigate to Facebook
            page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=15000)
            
            # Load cookies if provided
            if cookie_file:
                try:
                    logging.info(f"Loading cookies from: {cookie_file}")
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        cookies = []
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                cookie = {
                                    'name': parts[5],
                                    'value': parts[6],
                                    'domain': parts[0],
                                    'path': parts[2],
                                    'secure': parts[3] == 'TRUE',
                                    'httpOnly': parts[1] == 'TRUE',
                                    'sameSite': 'None' if parts[3] == 'TRUE' else 'Lax'
                                }
                                
                                if len(parts) > 4 and parts[4].isdigit():
                                    cookie['expires'] = int(parts[4])
                                
                                cookies.append(cookie)
                        
                        context.add_cookies(cookies)
                        logging.info(f"Loaded {len(cookies)} Facebook cookies")
                
                except Exception as e:
                    logging.error(f"Error loading cookies: {e}")
            
            # Navigate to the profile page
            page.goto(account_url, wait_until="domcontentloaded", timeout=30000)
            logging.info(f"Successfully navigated to: {account_url}")
            
            # Wait for page to load
            page.wait_for_timeout(3000)
            
            # Scroll to load posts
            for scroll in range(4):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                logging.info(f"Scroll {scroll + 1}/4")
            
            # Extract post links
            # Look for common Facebook post link patterns
            post_selectors = [
                'a[href*="/posts/"]',
                'a[href*="/photo/"]',
                'a[href*="/video/"]',
                'a[href*="/reel/"]',
                'a[href*="/watch/"]',
                'a[role="link"][href*="fbid="]'
            ]
            
            seen_links = set()
            
            for selector in post_selectors:
                try:
                    links = page.locator(selector).all()
                    
                    for link_element in links:
                        try:
                            href = link_element.get_attribute('href')
                            
                            if not href:
                                continue
                            
                            # Normalize URL
                            if href.startswith('/'):
                                href = f"https://web.facebook.com{href}"
                            elif not href.startswith('http'):
                                continue
                            
                            # Remove query parameters for deduplication
                            base_url = href.split('?')[0]
                            
                            # Skip if already found
                            if base_url in seen_links:
                                continue
                            
                            # Skip unwanted links
                            skip_patterns = [
                                '/about', '/community', '/groups', '/events', '/reviews',
                                '/stories/',  # Skip stories
                                '/reel/?',    # Skip generic reel tab (no ID)
                                '/watch/?',   # Skip generic watch tab (no ID)
                                '/photo/?set=',  # Skip album links without specific photo
                            ]
                            
                            if any(x in href for x in skip_patterns):
                                continue
                            
                            # Must have an actual ID (fbid=, specific post ID, etc.)
                            # Check if it's a real post with content
                            if '/reel/' in href and not any(c.isdigit() for c in href.split('/reel/')[-1]):
                                continue  # Skip /reel/ without ID
                            
                            if '/photo/' in href and 'fbid=' not in href:
                                continue  # Skip /photo/ without fbid
                            
                            if '/watch/' in href and not any(c.isdigit() for c in href.split('/watch/')[-1].split('?')[0]):
                                continue  # Skip /watch/ without video ID
                            
                            # Add to results
                            seen_links.add(base_url)
                            post_links.append(href)
                            logging.info(f"Found Facebook post: {href}")
                            
                            if len(post_links) >= max_posts:
                                break
                        
                        except Exception as e:
                            continue
                    
                    if len(post_links) >= max_posts:
                        break
                
                except Exception as e:
                    logging.debug(f"No links found with selector {selector}: {e}")
                    continue
            
            logging.info(f"Successfully collected {len(post_links)} Facebook posts")
            
            browser.close()
            
        except PlaywrightTimeout as e:
            logging.error(f"Timeout error: {e}")
        except Exception as e:
            logging.error(f"Error scraping Facebook page: {e}")
    
    return post_links[:max_posts]

