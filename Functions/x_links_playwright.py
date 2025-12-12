"""
X/Twitter Links Scraper - Playwright Version

Extracts recent post links from X/Twitter profiles.
"""

import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import config
import time


def x_scraper_recent_playwright(account_url: str, cookie_file: str = None, max_posts: int = 5) -> list:
    """
    Scrape recent X/Twitter posts using Playwright.
    
    Args:
        account_url: X/Twitter profile URL (e.g., https://x.com/username)
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
            
            logging.info(f"Navigating to X/Twitter profile: {account_url}")
            
            # Navigate to X/Twitter
            page.goto("https://x.com", wait_until="domcontentloaded", timeout=15000)
            
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
                        logging.info(f"Loaded {len(cookies)} X/Twitter cookies")
                
                except Exception as e:
                    logging.error(f"Error loading cookies: {e}")
            
            # Navigate to the profile page
            page.goto(account_url, wait_until="domcontentloaded", timeout=30000)
            logging.info(f"Successfully navigated to: {account_url}")
            
            # Extract username from URL
            profile_username = None
            try:
                profile_username = account_url.split('x.com/')[-1].split('?')[0].split('/')[0].lower()
                logging.info(f"Profile username: @{profile_username}")
            except:
                logging.warning("Could not extract username from URL")
            
            # Wait for page to load
            page.wait_for_timeout(3000)
            
            # Scroll to load posts
            for scroll in range(4):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                logging.info(f"Scroll {scroll + 1}/4")
            
            # Extract post links
            # Look for article elements (tweets) and find status links
            seen_links = set()
            
            try:
                # Find all tweet/post links with /status/
                links = page.locator('a[href*="/status/"]').all()
                
                for link_element in links:
                    try:
                        href = link_element.get_attribute('href')
                        
                        if not href:
                            continue
                        
                        # Normalize URL
                        if href.startswith('/'):
                            href = f"https://x.com{href}"
                        elif not href.startswith('http'):
                            continue
                        
                        # Must contain /status/ to be a real post
                        if '/status/' not in href:
                            continue
                        
                        # Skip analytics, photo, video sub-pages
                        skip_subpages = ['/analytics', '/photo/', '/video/', '/retweets', '/quotes', '/likes']
                        if any(sub in href for sub in skip_subpages):
                            continue
                        
                        # Remove query parameters for deduplication
                        base_url = href.split('?')[0]
                        
                        # Skip if already found
                        if base_url in seen_links:
                            continue
                        
                        # Extract username and tweet ID
                        try:
                            # Format: https://x.com/username/status/1234567890
                            parts = href.split('x.com/')[-1].split('/')
                            if len(parts) < 3:
                                continue
                            
                            tweet_username = parts[0].lower()
                            
                            # Only get posts from the profile owner
                            if profile_username and tweet_username != profile_username:
                                continue
                            
                            # Get tweet ID
                            status_idx = parts.index('status')
                            if status_idx + 1 >= len(parts):
                                continue
                            
                            tweet_id = parts[status_idx + 1].split('?')[0]
                            
                            # Must be numeric
                            if not tweet_id.isdigit():
                                continue
                            
                            # Skip very short IDs (invalid)
                            if len(tweet_id) < 10:
                                continue
                            
                            # Construct clean URL (no extra paths)
                            clean_url = f"https://x.com/{tweet_username}/status/{tweet_id}"
                            
                        except:
                            continue
                        
                        # Add to results
                        seen_links.add(clean_url)
                        post_links.append(clean_url)
                        logging.info(f"Found X/Twitter post: {clean_url}")
                        
                        if len(post_links) >= max_posts:
                            break
                    
                    except Exception as e:
                        continue
            
            except Exception as e:
                logging.error(f"Error extracting X/Twitter links: {e}")
            
            logging.info(f"Successfully collected {len(post_links)} X/Twitter posts")
            
            browser.close()
            
        except PlaywrightTimeout as e:
            logging.error(f"Timeout error: {e}")
        except Exception as e:
            logging.error(f"Error scraping X/Twitter profile: {e}")
    
    return post_links[:max_posts]

