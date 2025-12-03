"""
Facebook scraper module for social media links scraping - Modified for v2.
Uses modern CSS selectors and improved element detection for recent content monitoring.
"""

import logging
import time
from typing import List
from selenium.webdriver.common.by import By


def facebook_scraper_recent(driver, account_url: str, cookie_path: str, max_scrolls: int = 20) -> List[str]:
    """
    Scrape recent Facebook account video links with limited scrolling.
    
    Args:
        driver: Chrome WebDriver instance
        account_url: Facebook account URL to scrape
        cookie_path: Path to facebook.txt file containing cookies
        max_scrolls: Maximum number of scrolls (default 20 for recent content)
        
    Returns:
        List of video URLs
    """
    video_links = []
    processed_urls = set()
    
    try:
        # Initial setup and authentication
        driver.get("https://www.facebook.com")
        
        # Load cookies from facebook.txt file
        with open(cookie_path, 'r') as file:
            for line in file:
                if line.startswith('#') or not line.strip():
                    continue
                fields = line.strip().split('\t')
                if len(fields) >= 7:
                    cookie_dict = {
                        'name': fields[5],
                        'value': fields[6],
                        'domain': fields[0],
                        'path': fields[2]
                    }
                    if fields[3].lower() == 'true':
                        cookie_dict['secure'] = True
                    if fields[4] != '0' and fields[4].replace('.', '').isdigit():
                        try:
                            # Handle decimal expiry times by converting to int
                            expiry_value = float(fields[4])
                            cookie_dict['expiry'] = int(expiry_value)
                        except (ValueError, OverflowError):
                            # Skip cookies with invalid expiry values
                            continue
                    try:
                        driver.delete_cookie(fields[5])
                        driver.add_cookie(cookie_dict)
                    except Exception as e:
                        logging.warning(f"Error adding cookie {fields[5]}: {e}")
        
        driver.refresh()
        time.sleep(3)
        
        # Start scraping videos
        videos_url = account_url if account_url.endswith('/videos') else f"{account_url.rstrip('/')}/videos"
        driver.get(videos_url)
        time.sleep(5)
        
        scroll_count = 0
        while scroll_count < max_scrolls:
            videos_before = len(processed_urls)
            logging.info(f"Scroll {scroll_count + 1}: Processing videos, current count: {videos_before}")
            
            # Modern approach: Find video links using multiple CSS selectors
            video_selectors = [
                # Facebook Reels links
                'a[href*="/reel/"]',
                'a[href*="/videos/"]',
                'a[href*="facebook.com/"][href*="/videos/"]',
                # Generic video container links
                'a[aria-label*="video"]',
                'a[role="link"][href*="facebook.com"]'
            ]
            
            found_videos = []
            for selector in video_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href and ('/reel/' in href or '/videos/' in href):
                            if href not in processed_urls:
                                found_videos.append(href)
                                processed_urls.add(href)
                except Exception as e:
                    logging.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Alternative approach: Find video elements by structure
            try:
                # Look for video elements and find their parent links
                video_elements = driver.find_elements(By.TAG_NAME, 'video')
                for video_el in video_elements:
                    try:
                        # Find parent link
                        parent_link = video_el.find_element(By.XPATH, './ancestor::a[contains(@href, "facebook.com")]')
                        href = parent_link.get_attribute('href')
                        if href and href not in processed_urls:
                            found_videos.append(href)
                            processed_urls.add(href)
                    except:
                        continue
            except Exception as e:
                logging.debug(f"Video element search failed: {e}")
            
            # Alternative: Look for thumbnail images that indicate videos
            try:
                # Find video thumbnails and get their parent links
                thumbnails = driver.find_elements(By.CSS_SELECTOR, 'img[alt*="Video"], img[alt*="thumbnail"]')
                for thumb in thumbnails:
                    try:
                        parent_link = thumb.find_element(By.XPATH, './ancestor::a[contains(@href, "facebook.com")]')
                        href = parent_link.get_attribute('href')
                        if href and ('/reel/' in href or '/videos/' in href) and href not in processed_urls:
                            found_videos.append(href)
                            processed_urls.add(href)
                    except:
                        continue
            except Exception as e:
                logging.debug(f"Thumbnail search failed: {e}")
            
            # Process found videos
            new_videos_this_scroll = 0
            for video_url in found_videos:
                if video_url not in video_links:
                    video_links.append(video_url)
                    new_videos_this_scroll += 1
                    logging.info(f"Found video: {video_url}")
            
            videos_after = len(processed_urls)
            logging.info(f"Scroll {scroll_count + 1}: Found {new_videos_this_scroll} new videos ({videos_after} total processed)")
            
            # Scroll down to load more content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            scroll_count += 1
            
    except Exception as e:
        logging.error(f"Error processing Facebook account {account_url}: {e}")
        
    logging.info(f"Facebook scraper completed: {len(video_links)} videos collected")
    return video_links