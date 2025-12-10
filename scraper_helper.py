"""
Scraper Helper Module - Shared utilities for social media scraping

This module contains the SocialMediaScraper class which provides:
- Platform identification from URLs
- WebDriver creation and configuration
- Debug utilities for troubleshooting
"""

import logging
import os
from datetime import datetime
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from playwright.sync_api import sync_playwright
import config


class SocialMediaScraper:
    """Main scraper utility class for handling browser automation and platform detection"""
    
    def __init__(self):
        self.config = config.get_default_config()
        # Create debug screenshots directory
        self.debug_dir = "./debugger-screenshots"
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def setup_chrome_options(self):
        """Setup Chrome options for WebDriver"""
        chrome_options = uc.ChromeOptions()
        
        # Set Chrome binary path explicitly (if configured and not None)
        if hasattr(config, 'CHROME_BINARY_PATH') and config.CHROME_BINARY_PATH is not None:
            chrome_options.binary_location = config.CHROME_BINARY_PATH
        
        # Add Chrome arguments from config
        for arg in config.CHROME_ARGUMENTS:
            chrome_options.add_argument(arg)
        
        # Add headless mode if configured
        if self.config['headless_mode']:
            chrome_options.add_argument("--headless")
            
        return chrome_options
    
    def debug_screenshot(self, driver, step_name):
        """Take debug screenshot to see what browser is showing"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{step_name}_{timestamp}.png"
            filepath = os.path.join(self.debug_dir, filename)
            driver.save_screenshot(filepath)
            logging.info(f"Debug screenshot saved: {filepath}")
        except Exception as e:
            logging.warning(f"Could not save debug screenshot: {e}")
    
    def create_driver(self):
        """Create Chrome WebDriver instance"""
        logging.info("Creating Chrome driver... (this may take 30-60 seconds on first run)")
        
        try:
            # Try with version specification first
            chrome_options = self.setup_chrome_options()
            logging.info(f"Attempting to create driver with Chrome version {config.CHROME_VERSION}...")
            driver = uc.Chrome(options=chrome_options, version_main=config.CHROME_VERSION)
            
            # Take debug screenshot to verify it's working
            self.debug_screenshot(driver, "driver_created")
            return driver
        except Exception as e:
            logging.warning(f"Failed to create driver with Chrome version {config.CHROME_VERSION}: {e}")
            try:
                # Fallback to auto-detection with fresh options
                logging.info("Attempting driver creation with auto-detection...")
                chrome_options = self.setup_chrome_options()
                driver = uc.Chrome(options=chrome_options)
                
                # Take debug screenshot to verify it's working
                self.debug_screenshot(driver, "driver_created_auto")
                return driver
            except Exception as e:
                logging.error(f"Failed to create driver with auto-detection: {e}")
                # Last resort: use system Chrome with WebDriverManager
                try:
                    logging.info("Attempting driver creation with WebDriverManager (downloading driver if needed)...")
                    regular_options = webdriver.ChromeOptions()
                    # Add Chrome arguments from config
                    for arg in config.CHROME_ARGUMENTS:
                        regular_options.add_argument(arg)
                    
                    if self.config['headless_mode']:
                        regular_options.add_argument("--headless")
                    
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=regular_options)
                    
                    # Take debug screenshot to verify it's working
                    self.debug_screenshot(driver, "driver_created_fallback")
                    logging.info("✅ Chrome driver created successfully!")
                    return driver
                except Exception as e:
                    logging.error(f"All driver creation methods failed: {e}")
                    raise Exception("Could not create Chrome driver")
    
    def create_playwright_browser(self):
        """
        Create Playwright browser instance for Instagram.
        Returns (playwright, browser, context, page) tuple.
        """
        headless_mode = self.config['headless_mode']
        logging.info(f"Creating Playwright browser... (headless={headless_mode})")
        
        try:
            playwright = sync_playwright().start()
            
            # Launch browser with appropriate settings
            browser = playwright.chromium.launch(
                headless=headless_mode,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                ]
            )
            
            # Create browser context (like an incognito session)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Create a new page
            page = context.new_page()
            
            logging.info("✅ Playwright browser created successfully!")
            
            return playwright, browser, context, page
            
        except Exception as e:
            logging.error(f"Failed to create Playwright browser: {e}")
            raise Exception(f"Could not create Playwright browser: {e}")
    
    def identify_platform(self, url: str) -> str:
        """Identify social media platform from URL"""
        url = str(url).lower()
        if 'instagram.com' in url:
            return 'instagram'
        elif 'tiktok.com' in url:
            return 'tiktok'
        elif 'x.com' in url or 'twitter.com' in url:
            return 'x'
        elif 'facebook.com' in url or 'fb.com' in url:
            return 'facebook'
        elif 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        else:
            return 'unknown'

