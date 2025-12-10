"""
Instagram Links Scraper Module - Playwright Version

This module contains functions for scraping video links from Instagram profiles.
Uses Playwright for better performance and stealth.
"""

import logging
import time


def close_modal_playwright(page):
    """Close Instagram modal using Playwright"""
    try:
        # Method 1: Press ESC key
        page.keyboard.press('Escape')
        page.wait_for_timeout(300)
        return True
    except:
        pass
    
    try:
        # Method 2: Click close button
        close_btn = page.locator('svg[aria-label="Close"]').first
        if close_btn.is_visible():
            close_btn.click()
            page.wait_for_timeout(300)
            return True
    except:
        pass
    
    try:
        # Method 3: Navigate back if on post page
        current_url = page.url
        if '/reel/' in current_url or '/p/' in current_url:
            page.go_back()
            page.wait_for_timeout(500)
            return True
    except:
        pass
    
    return False


def instagram_scraper_recent_playwright(page, account_url: str, cookie_path: str, max_scrolls: int = 20) -> list:
    """
    Scrape recent video links from an Instagram account using Playwright.
    
    Args:
        page: Playwright Page instance
        account_url: Instagram account URL (e.g., https://www.instagram.com/username)
        cookie_path: Path to cookie file
        max_scrolls: Maximum number of scrolls (default 20 for recent content)
    
    Returns:
        List of video URLs
    """
    video_links = []
    processed_urls = set()
    
    try:
        # Navigate to Instagram
        logging.info("Navigating to Instagram...")
        page.goto("https://www.instagram.com", wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        
        # Load cookies
        logging.info("Loading cookies...")
        cookie_count = 0
        cookies_to_add = []
        
        with open(cookie_path, 'r') as file:
            for line in file:
                if line.startswith('#') or not line.strip():
                    continue
                fields = line.strip().split('\t')
                if len(fields) >= 7:
                    # Only load Instagram cookies
                    domain = fields[0]
                    if 'instagram.com' not in domain:
                        continue
                    
                    # Playwright cookie format
                    cookie_dict = {
                        'name': fields[5],
                        'value': fields[6],
                        'domain': domain if domain.startswith('.') else f'.{domain}',
                        'path': fields[2],
                        'secure': fields[3].lower() == 'true',
                    }
                    
                    # Handle expiry
                    if fields[4] != '0' and fields[4].isdigit():
                        try:
                            expiry_value = int(fields[4])
                            if expiry_value > int(time.time()):
                                cookie_dict['expires'] = expiry_value
                        except (ValueError, OverflowError):
                            pass
                    
                    cookies_to_add.append(cookie_dict)
                    cookie_count += 1
        
        # Add cookies to browser context
        page.context.add_cookies(cookies_to_add)
        logging.info(f"Loaded {cookie_count} Instagram cookies")
        
        # Refresh to apply cookies
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        
        # Navigate to the account
        logging.info(f"Processing Instagram account: {account_url}")
        page.goto(account_url, wait_until="domcontentloaded", timeout=15000)
        
        # Wait for posts grid to load (wait for at least one post link to appear)
        try:
            page.wait_for_selector('a[href*="/reel/"], a[href*="/p/"]', timeout=15000)
            logging.info("Posts grid loaded successfully")
            page.wait_for_timeout(1000)  # Small buffer for JS to finish
        except Exception as e:
            logging.warning(f"Posts grid didn't load within timeout: {e}")
            # Try waiting a bit longer in case of slow load
            page.wait_for_timeout(3000)
        
        # Collect pinned posts to skip them
        pinned_hrefs = set()
        try:
            pinned_icons = page.locator('svg[aria-label="Pinned post icon"]').all()
            for icon in pinned_icons:
                try:
                    parent_link = icon.locator('xpath=ancestor::a[contains(@href, "/reel/") or contains(@href, "/p/")]').first
                    href = parent_link.get_attribute('href')
                    if href:
                        href_path = href.replace('https://www.instagram.com', '')
                        pinned_hrefs.add(href_path)
                except:
                    continue
            
            if pinned_hrefs:
                logging.info(f"Found {len(pinned_hrefs)} pinned posts to skip")
        except Exception as e:
            logging.warning(f"Could not detect pinned posts: {e}")
        
        scroll_count = 0
        target_posts = 5  # Only need 5 posts
        
        while scroll_count < max_scrolls and len(video_links) < target_posts:
            # Get all posts on the page (reels, photos, carousels - everything)
            all_posts = page.locator('a[href*="/reel/"], a[href*="/p/"]').all()
            logging.info(f"Scroll {scroll_count + 1}: Found {len(all_posts)} total post elements")
            
            posts_processed_this_batch = 0
            
            for post in all_posts:
                # Stop if we have enough posts
                if len(video_links) >= target_posts:
                    break
                try:
                    href = post.get_attribute('href')
                    if not href:
                        continue
                    
                    # Make sure it's a full URL
                    if not href.startswith('http'):
                        href = f"https://www.instagram.com{href}"
                    
                    # Extract username from URL
                    # Format: https://www.instagram.com/USERNAME/reel/ID or /p/ID
                    path_parts = href.split('/')
                    if len(path_parts) >= 4:
                        post_username = path_parts[3]  # Get username from URL
                    else:
                        continue
                    
                    # Only get posts from the target account
                    target_username = account_url.rstrip('/').split('/')[-1]
                    if post_username != target_username:
                        logging.debug(f"Skipping post from different user: {post_username} (want: {target_username})")
                        continue
                    
                    # Extract path for comparison
                    href_path = href.replace('https://www.instagram.com', '')
                    
                    # Skip if already processed
                    if href_path in processed_urls:
                        continue
                    
                    # Skip invalid URLs
                    if '/liked_by/' in href_path or '/tagged/' in href_path:
                        continue
                    
                    # Skip pinned posts
                    if href_path in pinned_hrefs:
                        logging.info(f"Skipping pinned post: {href_path}")
                        continue
                    
                    processed_urls.add(href_path)
                    posts_processed_this_batch += 1
                    
                    # Add the post (no need to open modal or check if it's video)
                    video_links.append(href)
                    logging.info(f"Found post: {href}")
                    
                except Exception as e:
                    logging.error(f"Error processing post {href if 'href' in locals() else 'unknown'}: {e}")
                    continue
            
            logging.info(f"Scroll {scroll_count + 1}: Processed {posts_processed_this_batch} new posts")
            
            # Scroll down to load more content
            page.evaluate("window.scrollBy(0, 400)")
            page.wait_for_timeout(800)
            
            scroll_count += 1
        
        logging.info(f"Finished processing. Found {len(video_links)} posts.")
    
    except Exception as e:
        logging.error(f"Error processing Instagram account {account_url}: {e}")
    
    return video_links

