"""
Configuration file for Links Scraper v2

This file contains all configuration settings for the scraper including:
- File paths and cookies
- Browser configuration
- Platform-specific settings
- Database configuration
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (explicit path, override=True to override system env vars)
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
print(f"[CONFIG] Loading .env from: {env_path}")
print(f"[CONFIG] .env file exists: {env_path.exists()}")

# =============================================================================
# FILE PATHS AND DIRECTORIES
# =============================================================================

# Cookie file path (unified for all platforms)
UNIFIED_COOKIES_PATH = './cookies/cookies.txt'

# Facebook-specific cookie file path
FACEBOOK_COOKIES_PATH = './cookies/facebook.txt'

# YouTube-specific cookie file path
YOUTUBE_COOKIES_PATH = './cookies/youtube.txt'

# Directories
COOKIES_DIR = Path('./cookies')
FUNCTIONS_DIR = Path('./Functions')
LOGS_DIR = Path('./logs')

# =============================================================================
# BROWSER CONFIGURATION
# =============================================================================

# Browser settings - Load from .env file
HEADLESS_ENV_VALUE = os.getenv('HEADLESS', 'TRUE')
HEADLESS_MODE = HEADLESS_ENV_VALUE.upper() == 'TRUE'  # Read from .env file

# Debug output for headless mode (using print since logging not configured yet)
print(f"[CONFIG] HEADLESS env value: '{HEADLESS_ENV_VALUE}'")
print(f"[CONFIG] HEADLESS_MODE: {HEADLESS_MODE} (False = visible browser, True = hidden browser)")

CHROME_VERSION = 139  # Chrome version for undetected-chromedriver
# Auto-detect Chrome path based on OS (None = let undetected-chromedriver auto-detect)
CHROME_BINARY_PATH = None  # Will auto-detect Chrome installation

# Chrome browser arguments
CHROME_ARGUMENTS = [
    "--no-sandbox",
    "--disable-dev-shm-usage", 
    "--disable-gpu",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    "--disable-ipc-flooding-protection",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-translate",
    "--hide-scrollbars",
    "--mute-audio",
    "--disable-logging",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-client-side-phishing-detection",
    "--disable-default-apps",
    "--disable-hang-monitor",
    "--disable-prompt-on-repost",
    "--disable-sync",
    "--disable-web-resources",
    "--metrics-recording-only",
    "--no-first-run",
    "--safebrowsing-disable-auto-update",
    "--window-size=1920,1080"
]

# =============================================================================
# PLATFORM-SPECIFIC SETTINGS
# =============================================================================

# Max scrolls for recent content monitoring (v2 specific)
MAX_SCROLLS_PER_PLATFORM = {
    'instagram': 20,
    'tiktok': 20,
    'x': 20,
    'facebook': 20,
    'youtube': 50  # YouTube uses max_videos instead of scrolls
}

# TikTok settings
TIKTOK_API_KEY = 'bae3e23e1e998bccde1e852a105d099b'  # Replace with actual API key
TIKTOK_MAX_ATTEMPTS = 3
TIKTOK_RETRY_WAIT = 30

# TikTok container XPath patterns
TIKTOK_CONTAINER_XPATHS = [
    "/html/body/div[1]/div[2]/div[2]/div/div",
    "/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]",
    "/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[3]/div",
    "//div[contains(@class, 'DivTimelineTabContainer')]",
    "//div[@data-e2e='user-post-item-list']",
    "/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div"
]

# X/Twitter settings
X_MAX_NO_VIDEO_SCROLLS = 20
X_SCROLL_AMOUNT = 180000

# Facebook XPath patterns for different layouts
FACEBOOK_BASE_XPATH_PATTERNS = [
    "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[4]/div/div[5]/div/div/div/div[2]/div/div/div",
    "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[4]/div/div[2]/div/div/div/div[2]/div/div/div"
]

FACEBOOK_DATE_XPATH_PATTERNS = [
    "div/div/div/div/div/div[2]/span[1]/div[2]/div/div[1]/span[1]/div/div/div/span/span",
    "div/div/div/div/div/div[2]/span[1]/div[2]/div/div[1]/span[1]/div/div/div/span",
    "div/div/div/div/div/div[2]/span[1]/div[2]/div/div[1]/span[1]/span/span/span"
]

FACEBOOK_MAX_SCROLL_ATTEMPTS = 300
FACEBOOK_CONSECUTIVE_NO_NEW_VIDEOS_LIMIT = 3

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

DATABASE_URL = 'sqlite:///links_scraper_v2.db'

# =============================================================================
# SCHEDULER CONFIGURATION
# =============================================================================

# Round-robin scheduler settings
SCHEDULER_INTERVAL = 30  # seconds between account checks
SCHEDULER_ENABLED = True

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Logging settings
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_HANDLERS = [logging.StreamHandler()]

def configure_logging():
    """Configure logging with the settings defined above"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=LOG_HANDLERS
    )

# =============================================================================
# DEFAULT CONFIGURATION DICTIONARY
# =============================================================================

def get_default_config():
    """
    Get the default configuration dictionary for the scraper.
    
    Returns:
        dict: Default configuration settings
    """
    return {
        # File paths
        'unified_cookies': UNIFIED_COOKIES_PATH,
        'facebook_cookies': FACEBOOK_COOKIES_PATH,
        'youtube_cookies': YOUTUBE_COOKIES_PATH,
        
        # API keys
        'tiktok_api_key': TIKTOK_API_KEY,
        
        # Browser configuration
        'headless_mode': HEADLESS_MODE,
        
        # Platform-specific settings
        'max_scrolls': MAX_SCROLLS_PER_PLATFORM
    }

# =============================================================================
# DIRECTORY SETUP
# =============================================================================

def create_directories():
    """Create necessary directories if they don't exist"""
    COOKIES_DIR.mkdir(exist_ok=True)
    FUNCTIONS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================

def validate_config(config: dict) -> bool:
    """
    Validate configuration settings.
    
    Args:
        config (dict): Configuration dictionary to validate
        
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    required_keys = [
        'unified_cookies',
        'facebook_cookies',
        'youtube_cookies',
        'tiktok_api_key', 
        'headless_mode',
        'max_scrolls'
    ]
    
    for key in required_keys:
        if key not in config:
            logging.error(f"Missing required configuration key: {key}")
            return False
    
    # Validate cookie file exists
    if not Path(config['unified_cookies']).exists():
        logging.warning(f"Cookie file not found: {config['unified_cookies']}")
    
    return True
