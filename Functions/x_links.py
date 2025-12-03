"""
X/Twitter Links Scraper Module - Modified for v2

This module contains functions for scraping video links from X/Twitter profiles.
Uses BeautifulSoup for HTML parsing with limited scrolling for recent content.
"""

import logging
import time
import undetected_chromedriver as uc
from selenium import webdriver
from bs4 import BeautifulSoup


def load_cookies(driver, cookie_path):
    """
    Load cookies from file into the driver.
    
    Args:
        driver: Selenium WebDriver instance
        cookie_path: Path to cookie file
        
    Returns:
        bool: True if cookies loaded successfully, False otherwise
    """
    try:
        logging.info("Loading X/Twitter cookies...")
        cookie_count = 0
        with open(cookie_path, 'r') as file:
            for line in file:
                if line.startswith('#') or not line.strip():
                    continue
                fields = line.strip().split('\t')
                if len(fields) >= 7:
                    # Only load X/Twitter cookies
                    domain = fields[0]
                    if 'x.com' not in domain and 'twitter.com' not in domain:
                        continue
                    
                    cookie_dict = {
                        'name': fields[5],
                        'value': fields[6],
                        'domain': domain,
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
                        cookie_count += 1
                    except Exception as e:
                        logging.warning(f"Skipped cookie {fields[5]}: {str(e)[:50]}...")
                        
        logging.info(f"Loaded {cookie_count} X/Twitter cookies")
        
        # Verify cookies were actually loaded
        current_cookies = driver.get_cookies()
        if len(current_cookies) < cookie_count * 0.5:  # At least 50% of cookies should load
            logging.error(f"Cookie verification failed. Expected {cookie_count}, got {len(current_cookies)}")
            return False
        return True
        
    except Exception as e:
        logging.error(f"Error loading cookies: {e}")
        return False


def x_scraper_recent(driver, account_url: str, cookie_path: str, max_scrolls: int = 20) -> list:
    """
    Scrape recent video links from an X/Twitter account with limited scrolling.
    
    Args:
        driver: Selenium WebDriver instance
        account_url: X/Twitter account URL (e.g., https://x.com/username)
        cookie_path: Path to cookie file
        max_scrolls: Maximum number of scrolls (default 20 for recent content)
    
    Returns:
        List of video URLs
    """
    video_links = []
    seen_urls = set()
    
    try:
        # Navigate to X.com and handle any redirects/consent pages
        logging.info("Navigating to x.com...")
        driver.get("https://x.com")
        time.sleep(5)
        
        # Check if we're on a consent/redirect page and try to proceed
        current_url = driver.current_url.lower()
        if 'consent' in current_url or 'google' in current_url or 'before' in current_url:
            logging.info(f"Detected consent/redirect page: {driver.current_url}")
            # Try to find and click "Accept" or "Continue" buttons
            try:
                # Common consent page button selectors
                consent_buttons = [
                    "//button[contains(text(), 'Accept')]",
                    "//button[contains(text(), 'Alle akzeptieren')]", 
                    "//button[contains(text(), 'Continue')]",
                    "//button[@id='L2AGLb']",  # Google consent "Accept all"
                    "//a[contains(text(), 'Continue')]"
                ]
                
                for button_xpath in consent_buttons:
                    try:
                        from selenium.webdriver.common.by import By
                        button = driver.find_element(By.XPATH, button_xpath)
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(3)
                        logging.info(f"Clicked consent button: {button_xpath}")
                        break
                    except:
                        continue
                        
                # Wait and check if we're redirected
                time.sleep(5)
                if 'x.com' not in driver.current_url.lower():
                    # If still not on X.com, try direct navigation
                    driver.get("https://x.com")
                    time.sleep(5)
                    
            except Exception as e:
                logging.warning(f"Could not handle consent page: {e}")
                # Try direct navigation anyway
                driver.get("https://x.com")
                time.sleep(5)
        
        cookies_loaded = load_cookies(driver, cookie_path)
        
        if cookies_loaded:
            driver.refresh()
            time.sleep(5)
            logging.info("Cookies loaded successfully")
        else:
            logging.warning("Failed to load cookies, continuing without authentication")
        
        # Start scraping the account
        logging.info(f"Processing X account: {account_url}")
        driver.get(account_url)
        time.sleep(5)
        
        scroll_count = 0
        while scroll_count < max_scrolls:
            videos_before = len(seen_urls)
            
            html_source = driver.page_source
            soup = BeautifulSoup(html_source, 'lxml')
            video_divs = soup.find_all('div', style=True)
            
            for video_div in video_divs:
                style = video_div.get('style', '')
                if 'translateY' in style:
                    video_component = video_div.find('div', {'data-testid': 'videoPlayer'})
                    if not video_component:
                        continue
                    
                    post_div = video_div.find('div', class_='css-175oi2r r-18u37iz r-1q142lx')
                    if post_div:
                        post_link = post_div.find('a', href=True)
                        time_element = post_div.find('time')
                        post_date = time_element['datetime'][:10] if time_element else None
                        
                        if post_link:
                            post_url = f"https://twitter.com{post_link['href']}"
                            if post_url not in seen_urls:
                                seen_urls.add(post_url)
                                video_links.append(post_url)
                                logging.info(f"Found video: {post_url} from {post_date if post_date else 'unknown date'}")
            
            videos_after = len(seen_urls)
            logging.info(f"Scroll {scroll_count + 1}: Found {videos_after - videos_before} new videos")
            
            # Scroll down and wait for content to load
            scroll_amount = 180000
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(2)
            
            scroll_count += 1
            
    except Exception as e:
        logging.error(f"Error processing X account {account_url}: {e}")
    
    return video_links
