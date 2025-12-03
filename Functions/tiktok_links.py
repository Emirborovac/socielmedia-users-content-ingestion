"""
TikTok scraper module for social media links scraping - Modified for v2.
Uses limited scrolling for recent content monitoring.
"""

import logging
import time
from typing import List
from selenium.webdriver.common.by import By


def tiktok_scraper_recent(driver, account_url: str, cookie_path: str, max_scrolls: int = 20) -> List[str]:
    """
    Scrape recent TikTok account video links with limited scrolling.
    
    Args:
        driver: Chrome WebDriver instance
        account_url: TikTok account URL to scrape
        cookie_path: Path to cookies file
        max_scrolls: Maximum number of scrolls (default 20 for recent content)
        
    Returns:
        List of video URLs
    """
    video_links = []
    processed_urls = set()
    
    # TikTok container XPath patterns
    CONTAINER_XPATHS = [
        "/html/body/div[1]/div[2]/div[2]/div/div",
        "/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]",
        "/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[3]/div",
        "//div[contains(@class, 'DivTimelineTabContainer')]",
        "//div[@data-e2e='user-post-item-list']",
        "/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div"
    ]
    
    def extract_posts():
        """Extract posts from the current page using multiple XPath patterns."""
        recent_posts = []
        for xpath in CONTAINER_XPATHS:
            try:
                container = driver.find_element(By.XPATH, xpath)
                posts = container.find_elements(By.XPATH, './/div[@data-e2e="user-post-item"]//a')
                if posts:
                    links = [p.get_attribute('href') for p in posts]
                    filtered_links = [link for link in links if link not in processed_urls]
                    recent_posts.extend(filtered_links)
                    for link in filtered_links:
                        processed_urls.add(link)
                    if filtered_links:
                        logging.info(f"Found {len(filtered_links)} new posts using xpath: {xpath}")
                    return list(dict.fromkeys(recent_posts))  # Remove duplicates
            except Exception as e:
                logging.error(f"XPath {xpath} failed: {str(e)}")
                continue
        return []
    
    try:
        # Initial setup
        logging.info("Loading TikTok...")
        driver.get("https://www.tiktok.com")
        
        # Load cookies
        logging.info("Loading cookies...")
        with open(cookie_path, 'r') as file:
            for line in file:
                if line.startswith('#') or not line.strip():
                    continue
                fields = line.strip().split('\t')
                if len(fields) >= 7:
                    # Only load TikTok cookies
                    if 'tiktok.com' not in fields[0]:
                        continue
                    
                    cookie_dict = {
                        'name': fields[5],
                        'value': fields[6],
                        'domain': fields[0],
                        'path': fields[2]
                    }
                    
                    # Handle secure flag
                    if fields[3].lower() == 'true':
                        cookie_dict['secure'] = True
                    
                    # Handle expiry - skip cookies with invalid expiry values
                    if fields[4] != '0' and fields[4].isdigit():
                        try:
                            expiry_value = int(fields[4])
                            # Only set expiry if it's a reasonable future timestamp
                            if expiry_value > int(time.time()):
                                cookie_dict['expiry'] = expiry_value
                        except (ValueError, OverflowError):
                            # Skip cookies with invalid expiry values
                            continue
                    
                    try:
                        driver.delete_cookie(fields[5])
                        driver.add_cookie(cookie_dict)
                    except Exception as e:
                        logging.warning(f"Skipped cookie {fields[5]}: {str(e)[:50]}...")
        
        driver.refresh()
        time.sleep(5)
        
        # Process account
        logging.info(f"Processing TikTok account: {account_url}")
        driver.get(account_url)
        time.sleep(5)
        
        # Scroll and extract with limited scrolls
        scroll_count = 0
        while scroll_count < max_scrolls:
            # Get new posts
            new_links = extract_posts()
            if new_links:
                video_links.extend(new_links)
                logging.info(f"Scroll {scroll_count + 1}: Total videos found: {len(video_links)}")
            
            # Scroll down
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)  # Wait for content to load
            
            scroll_count += 1
        
        logging.info(f"Successfully collected {len(video_links)} video links")
            
    except Exception as e:
        logging.error(f"Error processing TikTok account {account_url}: {str(e)}")
    
    return video_links
