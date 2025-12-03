"""
Links Scraper v2 - Main Flask Application

Enterprise-grade social media links scraper with continuous monitoring.
Supports Instagram, TikTok, X/Twitter, Facebook, and YouTube.
"""

from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import logging
import threading
import time
import csv
import io
import json
import hashlib
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import config
import os

# Import scraper functions
from Functions.instagram_links import instagram_scraper_recent
from Functions.tiktok_links import tiktok_scraper_recent
from Functions.x_links import x_scraper_recent
from Functions.fb_links import facebook_scraper_recent
from Functions.youtube_links import youtube_scraper_recent

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.ensure_ascii = False

# Initialize database
db = SQLAlchemy(app)

# Configure logging
config.configure_logging()
logging.info("Links Scraper v2 starting up...")

# =============================================================================
# DATABASE MODELS
# =============================================================================

class Account(db.Model):
    """Social media account model"""
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, paused, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    
    # Relationship to video links
    video_links = db.relationship('VideoLink', backref='account', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Account {self.username} ({self.platform})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'platform': self.platform,
            'username': self.username,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'last_error': self.last_error,
            'video_count': len(self.video_links)
        }


class VideoLink(db.Model):
    """Video link model"""
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    url_hash = db.Column(db.String(64), nullable=False, index=True)  # For duplicate detection
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_date = db.Column(db.String(20))  # Date from the social media post
    
    # Unique constraint to prevent duplicates
    __table_args__ = (db.UniqueConstraint('account_id', 'url_hash', name='unique_account_video'),)
    
    def __repr__(self):
        return f'<VideoLink {self.url}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'url': self.url,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None,
            'post_date': self.post_date
        }


class SystemSettings(db.Model):
    """System settings model for persistent configuration"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemSettings {self.key}: {self.value}>'
    
    @staticmethod
    def get_setting(key: str, default_value: str = None):
        """Get a system setting value"""
        setting = SystemSettings.query.filter_by(key=key).first()
        return setting.value if setting else default_value
    
    @staticmethod
    def set_setting(key: str, value: str):
        """Set a system setting value"""
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = SystemSettings(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class SocialMediaScraper:
    """Main scraper class for handling all platforms"""
    
    def __init__(self):
        self.config = config.get_default_config()
        # Create debug screenshots directory
        self.debug_dir = "/home/root01/links-scraper-v2/debugger-screenshots"
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def setup_chrome_options(self):
        """Setup Chrome options for WebDriver"""
        chrome_options = uc.ChromeOptions()
        
        # Set Chrome binary path explicitly
        chrome_options.binary_location = config.CHROME_BINARY_PATH
        
        # Add Chrome arguments from config
        for arg in config.CHROME_ARGUMENTS:
            chrome_options.add_argument(arg)
        
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
        try:
            # Try with version specification first
            chrome_options = self.setup_chrome_options()
            driver = uc.Chrome(options=chrome_options, version_main=config.CHROME_VERSION)
            
            # Take debug screenshot to verify it's working
            self.debug_screenshot(driver, "driver_created")
            return driver
        except Exception as e:
            logging.warning(f"Failed to create driver with Chrome version {config.CHROME_VERSION}: {e}")
            try:
                # Fallback to auto-detection with fresh options
                chrome_options = self.setup_chrome_options()
                driver = uc.Chrome(options=chrome_options)
                
                # Take debug screenshot to verify it's working
                self.debug_screenshot(driver, "driver_created_auto")
                return driver
            except Exception as e:
                logging.error(f"Failed to create driver with auto-detection: {e}")
                # Last resort: use system Chrome with WebDriverManager
                try:
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
                    return driver
                except Exception as e:
                    logging.error(f"All driver creation methods failed: {e}")
                    raise Exception("Could not create Chrome driver")
    
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
    
    def scrape_account(self, account: Account, scheduler=None) -> list:
        """Scrape a single account for recent videos"""
        platform = account.platform
        account_url = account.url
        max_scrolls = self.config['max_scrolls'].get(platform, 20)
        
        logging.info(f"Scraping {platform} account: {account_url}")
        
        driver = None
        video_links = []
        
        try:
            # YouTube doesn't need browser - uses yt-dlp only
            if platform == 'youtube':
                video_links = youtube_scraper_recent(
                    None, account_url, self.config['youtube_cookies'], max_scrolls
                )
            else:
                # Other platforms need browser
                driver = self.create_driver()
                
                # Track the driver in scheduler if provided
                if scheduler:
                    scheduler.active_drivers.append(driver)
                
                # Take screenshot before scraping
                self.debug_screenshot(driver, f"before_scraping_{platform}")
                
                # Call appropriate scraper based on platform
                if platform == 'instagram':
                    video_links = instagram_scraper_recent(
                        driver, account_url, self.config['unified_cookies'], max_scrolls
                    )
                elif platform == 'tiktok':
                    video_links = tiktok_scraper_recent(
                        driver, account_url, self.config['unified_cookies'], max_scrolls
                    )
                elif platform == 'x':
                    video_links = x_scraper_recent(
                        driver, account_url, self.config['unified_cookies'], max_scrolls
                    )
                elif platform == 'facebook':
                    video_links = facebook_scraper_recent(
                        driver, account_url, self.config['facebook_cookies'], max_scrolls
                    )
                
                # Take screenshot after scraping
                if driver:
                    self.debug_screenshot(driver, f"after_scraping_{platform}")
            
            logging.info(f"Found {len(video_links)} videos for {account.username}")
            
        except Exception as e:
            error_msg = f"Error scraping {platform} account {account_url}: {e}"
            logging.error(error_msg)
            account.last_error = str(e)
            raise e
        finally:
            # Only cleanup driver if it was created (not for YouTube)
            if driver and platform != 'youtube':
                try:
                    # Remove from active drivers list
                    if scheduler and driver in scheduler.active_drivers:
                        scheduler.active_drivers.remove(driver)
                    driver.quit()
                except:
                    pass
        
        return video_links


# =============================================================================
# SCHEDULER
# =============================================================================

class RoundRobinScheduler:
    """Round-robin scheduler for continuous account monitoring"""
    
    def __init__(self, scraper: SocialMediaScraper):
        self.scraper = scraper
        self.running = False
        self.thread = None
        self.active_drivers = []  # Track active browser instances
    
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            
            # Save scheduler state to database
            with app.app_context():
                SystemSettings.set_setting('scheduler_status', 'running')
            
            logging.info("Round-robin scheduler started")
    
    def stop(self):
        """Stop the scheduler and cleanup all resources"""
        logging.info("Stopping scheduler and cleaning up resources...")
        self.running = False
        
        # Force close all active browser instances
        self.cleanup_all_browsers()
        
        # Wait for thread to finish
        if self.thread:
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                logging.warning("Scheduler thread did not stop gracefully")
        
        # Save scheduler state to database
        with app.app_context():
            SystemSettings.set_setting('scheduler_status', 'stopped')
        
        logging.info("Round-robin scheduler stopped and cleaned up")
    
    def cleanup_all_browsers(self):
        """Force close all active browser instances"""
        try:
            import psutil
            import os
            
            # Kill all Chrome/Chromium processes that might be hanging
            chrome_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and any(name in proc.info['name'].lower() for name in ['chrome', 'chromium', 'chromedriver']):
                        # Check if it's related to our scraper (look for undetected_chromedriver or our patterns)
                        if proc.info['cmdline'] and any('undetected' in str(cmd) or 'chromedriver' in str(cmd) for cmd in proc.info['cmdline']):
                            chrome_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Terminate Chrome processes
            for proc in chrome_processes:
                try:
                    logging.info(f"Terminating Chrome process: {proc.pid}")
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Wait a bit and kill any remaining processes
            time.sleep(2)
            for proc in chrome_processes:
                try:
                    if proc.is_running():
                        logging.info(f"Force killing Chrome process: {proc.pid}")
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except ImportError:
            logging.warning("psutil not available, cannot force cleanup Chrome processes")
            # Fallback: try to close tracked drivers
            for driver in self.active_drivers:
                try:
                    driver.quit()
                except:
                    pass
        
        # Clear the active drivers list
        self.active_drivers.clear()
    
    def get_persistent_status(self):
        """Get the persistent scheduler status from database"""
        try:
            with app.app_context():
                status = SystemSettings.get_setting('scheduler_status', 'stopped')
                return status == 'running'
        except:
            return False
    
    def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                with app.app_context():
                    # Get all active accounts
                    accounts = Account.query.filter_by(status='active').all()
                    
                    if not accounts:
                        logging.info("No active accounts to process")
                        time.sleep(config.SCHEDULER_INTERVAL)
                        continue
                    
                    for account in accounts:
                        if not self.running:
                            break
                        
                        try:
                            logging.info(f"Processing account: {account.username} ({account.platform})")
                            
                            # Scrape the account (pass scheduler for tracking)
                            video_links = self.scraper.scrape_account(account, scheduler=self)
                            
                            # Process and save new video links
                            new_links_count = 0
                            for video_url in video_links:
                                # Create hash for duplicate detection
                                url_hash = hashlib.sha256(video_url.encode()).hexdigest()
                                
                                # Check if link already exists
                                existing_link = VideoLink.query.filter_by(
                                    account_id=account.id, url_hash=url_hash
                                ).first()
                                
                                if not existing_link:
                                    # Add new video link
                                    video_link = VideoLink(
                                        account_id=account.id,
                                        url=video_url,
                                        url_hash=url_hash
                                    )
                                    db.session.add(video_link)
                                    new_links_count += 1
                            
                            # Update account status
                            account.last_checked = datetime.utcnow()
                            account.last_error = None
                            account.status = 'active'
                            
                            db.session.commit()
                            
                            logging.info(f"Processed {account.username}: {new_links_count} new videos found")
                            
                        except Exception as e:
                            # Handle account-specific errors
                            logging.error(f"Error processing account {account.username}: {e}")
                            account.last_error = str(e)
                            account.last_checked = datetime.utcnow()
                            account.status = 'error'
                            db.session.commit()
                        
                        # Sleep between accounts to avoid rate limiting
                        if self.running:
                            time.sleep(config.SCHEDULER_INTERVAL)
                
            except Exception as e:
                logging.error(f"Scheduler error: {e}")
                time.sleep(config.SCHEDULER_INTERVAL)


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

scraper = SocialMediaScraper()
scheduler = RoundRobinScheduler(scraper)


# =============================================================================
# FLASK ROUTES
# =============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/add-account')
def add_account_page():
    """Add account page"""
    return render_template('add_account.html')


@app.route('/accounts')
def accounts_page():
    """Accounts list page"""
    return render_template('accounts.html')


@app.route('/account/<int:account_id>/links')
def account_links_page(account_id):
    """Account links page"""
    account = Account.query.get_or_404(account_id)
    return render_template('account_links.html', account=account)


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Get all accounts"""
    accounts = Account.query.all()
    return jsonify([account.to_dict() for account in accounts])


@app.route('/api/accounts', methods=['POST'])
def add_account():
    """Add a new account"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400
    
    url = data['url'].strip()
    platform = scraper.identify_platform(url)
    
    if platform == 'unknown':
        return jsonify({'error': 'Unsupported platform'}), 400
    
    # Extract username from URL
    username = url.split('/')[-1] or url.split('/')[-2]
    
    # Check if account already exists
    existing_account = Account.query.filter_by(url=url).first()
    if existing_account:
        return jsonify({'error': 'Account already exists'}), 409
    
    # Create new account
    account = Account(
        url=url,
        platform=platform,
        username=username,
        status='active'
    )
    
    db.session.add(account)
    db.session.commit()
    
    logging.info(f"Added new account: {username} ({platform})")
    
    return jsonify(account.to_dict()), 201


@app.route('/api/accounts/bulk', methods=['POST'])
def add_accounts_bulk():
    """Add multiple accounts from CSV data"""
    data = request.get_json()
    
    if not data or 'accounts' not in data:
        return jsonify({'error': 'Accounts data is required'}), 400
    
    accounts_data = data['accounts']
    added_accounts = []
    errors = []
    
    for account_data in accounts_data:
        try:
            url = account_data.get('url', '').strip()
            if not url:
                errors.append({'url': url, 'error': 'URL is required'})
                continue
            
            platform = scraper.identify_platform(url)
            if platform == 'unknown':
                errors.append({'url': url, 'error': 'Unsupported platform'})
                continue
            
            # Extract username from URL
            username = url.split('/')[-1] or url.split('/')[-2]
            
            # Check if account already exists
            existing_account = Account.query.filter_by(url=url).first()
            if existing_account:
                errors.append({'url': url, 'error': 'Account already exists'})
                continue
            
            # Create new account
            account = Account(
                url=url,
                platform=platform,
                username=username,
                status='active'
            )
            
            db.session.add(account)
            added_accounts.append(account.to_dict())
            
        except Exception as e:
            errors.append({'url': account_data.get('url', ''), 'error': str(e)})
    
    db.session.commit()
    
    logging.info(f"Bulk added {len(added_accounts)} accounts")
    
    return jsonify({
        'added': added_accounts,
        'errors': errors,
        'total_added': len(added_accounts),
        'total_errors': len(errors)
    })


@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Delete an account"""
    account = Account.query.get_or_404(account_id)
    username = account.username
    
    db.session.delete(account)
    db.session.commit()
    
    logging.info(f"Deleted account: {username}")
    
    return jsonify({'message': 'Account deleted successfully'})


@app.route('/api/accounts/<int:account_id>/toggle', methods=['POST'])
def toggle_account_status(account_id):
    """Toggle account status (active/paused)"""
    account = Account.query.get_or_404(account_id)
    
    if account.status == 'active':
        account.status = 'paused'
    elif account.status in ['paused', 'error']:
        account.status = 'active'
    
    db.session.commit()
    
    return jsonify(account.to_dict())


@app.route('/api/accounts/<int:account_id>/links', methods=['GET'])
def get_account_links(account_id):
    """Get all video links for an account"""
    account = Account.query.get_or_404(account_id)
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Get video links with pagination
    video_links = VideoLink.query.filter_by(account_id=account_id)\
        .order_by(VideoLink.discovered_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'account': account.to_dict(),
        'links': [link.to_dict() for link in video_links.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': video_links.total,
            'pages': video_links.pages,
            'has_next': video_links.has_next,
            'has_prev': video_links.has_prev
        }
    })


@app.route('/api/accounts/<int:account_id>/links/export', methods=['GET'])
def export_account_links(account_id):
    """Export account video links to CSV"""
    account = Account.query.get_or_404(account_id)
    video_links = VideoLink.query.filter_by(account_id=account_id)\
        .order_by(VideoLink.discovered_at.desc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['URL', 'Discovered At', 'Post Date'])
    
    # Write data
    for link in video_links:
        writer.writerow([
            link.url,
            link.discovered_at.isoformat() if link.discovered_at else '',
            link.post_date or ''
        ])
    
    # Create response
    output.seek(0)
    
    # Create a BytesIO object for the response
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    
    filename = f"{account.username}_{account.platform}_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        mem,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )


@app.route('/api/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get scheduler status"""
    # Get persistent status from database
    persistent_status = scheduler.get_persistent_status()
    
    return jsonify({
        'running': persistent_status,
        'enabled': config.SCHEDULER_ENABLED,
        'thread_running': scheduler.running  # For debugging
    })


@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """Start the scheduler"""
    if config.SCHEDULER_ENABLED:
        scheduler.start()
        return jsonify({'message': 'Scheduler started'})
    else:
        return jsonify({'error': 'Scheduler is disabled'}), 400


@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Stop the scheduler"""
    scheduler.stop()
    return jsonify({'message': 'Scheduler stopped'})


# =============================================================================
# APPLICATION STARTUP
# =============================================================================

def initialize_app():
    """Initialize the application"""
    # Create directories
    config.create_directories()
    
    # Create database tables
    try:
        with app.app_context():
            db.create_all()
            logging.info("Database tables created successfully")
            
            # Test database connection
            result = db.session.execute(db.text('SELECT 1')).fetchone()
            if result:
                logging.info("Database connection verified")
                
            # Check if scheduler should be running based on persistent status
            if config.SCHEDULER_ENABLED:
                persistent_status = SystemSettings.get_setting('scheduler_status', 'stopped')
                if persistent_status == 'running':
                    logging.info("Restoring scheduler to running state from persistent settings")
                    scheduler.start()
                else:
                    logging.info("Scheduler remains stopped based on persistent settings")
                    
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise


if __name__ == '__main__':
    initialize_app()
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=2020,
        debug=False,
        threaded=True
    )
