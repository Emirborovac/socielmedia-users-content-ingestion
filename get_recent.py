"""
FastAPI endpoint for getting recent video posts from social media accounts.

Uses async queue system with SQLite persistence:
- GET /get_recent/{account_identifier} - Queues operation, returns operation_id immediately
- GET /get_recent/results/{operation_id} - Check operation status and get results
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import logging
import hashlib
import uuid
import threading
import time
import json
import config
import os

# Import scraper functions
from Functions.instagram_links import instagram_scraper_recent
from Functions.tiktok_links import tiktok_scraper_recent
from Functions.x_links import x_scraper_recent
from Functions.fb_links import facebook_scraper_recent
from Functions.youtube_links import youtube_scraper_recent

# Import scraper class for driver creation and platform identification
from app import SocialMediaScraper

# Configure logging
config.configure_logging()

# FastAPI app
app = FastAPI(title="Get Recent Posts API")

# Database setup
engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class Account(Base):
    __tablename__ = 'account'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True, nullable=False)
    platform = Column(String(50), nullable=False)
    username = Column(String(100), nullable=False)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime)
    last_error = Column(Text)
    
    video_links = relationship('VideoLink', backref='account', lazy=True, cascade='all, delete-orphan')


class VideoLink(Base):
    __tablename__ = 'video_link'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    url = Column(String(500), nullable=False)
    url_hash = Column(String(64), nullable=False, index=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    post_date = Column(String(20))


class Operation(Base):
    """Operation queue model for async processing"""
    __tablename__ = 'operation'
    
    id = Column(Integer, primary_key=True)
    operation_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    account_url = Column(String(500), nullable=False)
    platform = Column(String(50), nullable=False)
    username = Column(String(100), nullable=False)
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    result_links = Column(JSON)  # Store array of links as JSON
    error_message = Column(Text)
    account_id = Column(Integer, ForeignKey('account.id'), nullable=True)
    
    def to_dict(self):
        return {
            'operation_id': self.operation_id,
            'account_url': self.account_url,
            'platform': self.platform,
            'username': self.username,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result_links': self.result_links if self.result_links else [],
            'error_message': self.error_message
        }


# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Initialize scraper
scraper = SocialMediaScraper()


def normalize_account_url(account_identifier: str) -> tuple:
    """
    Normalize account identifier to full URL and extract username.
    
    Args:
        account_identifier: Can be a full URL or just username
        
    Returns:
        tuple: (normalized_url, username, platform)
    """
    identifier = account_identifier.strip()
    
    # If it's already a full URL
    if identifier.startswith('http://') or identifier.startswith('https://'):
        url = identifier
    else:
        # If it contains platform domain, add https://
        if 'instagram.com' in identifier or 'tiktok.com' in identifier or 'x.com' in identifier or 'twitter.com' in identifier or 'facebook.com' in identifier or 'youtube.com' in identifier:
            url = f"https://{identifier}"
        else:
            # Assume it's just a username - default to Instagram
            url = f"https://www.instagram.com/{identifier}"
    
    # Identify platform
    platform = scraper.identify_platform(url)
    
    # Extract username from URL and normalize URL format
    if platform == 'instagram':
        username = url.split('instagram.com/')[-1].split('/')[0].split('?')[0]
        url = f"https://www.instagram.com/{username}"
    elif platform == 'tiktok':
        if '@' in url:
            username = url.split('@')[-1].split('/')[0].split('?')[0]
        else:
            username = url.split('tiktok.com/')[-1].split('/')[0].split('?')[0]
        url = f"https://www.tiktok.com/@{username}" if not username.startswith('@') else f"https://www.tiktok.com/{username}"
    elif platform == 'x':
        username = url.split('x.com/')[-1].split('/')[0].split('?')[0] if 'x.com' in url else url.split('twitter.com/')[-1].split('/')[0].split('?')[0]
        url = f"https://x.com/{username}"
    elif platform == 'facebook':
        username = url.split('facebook.com/')[-1].split('/')[0].split('?')[0]
        url = f"https://www.facebook.com/{username}"
    elif platform == 'youtube':
        # YouTube URLs are more complex - preserve the original format
        if '/channel/' in url or '/user/' in url or '/@' in url:
            username = url.split('/')[-1].split('?')[0]
        else:
            username = url.split('youtube.com/')[-1].split('/')[0].split('?')[0]
        # Keep original URL format for YouTube
        if not url.startswith('http'):
            url = f"https://www.youtube.com/{username}"
    else:
        username = url.split('/')[-1].split('?')[0]
    
    return url, username, platform


class OperationQueueProcessor:
    """Background worker to process queued operations"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.scraper = SocialMediaScraper()
        self.processing_interval = 2  # Check for new operations every 2 seconds
    
    def start(self):
        """Start the background worker"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._process_queue, daemon=True)
            self.thread.start()
            logging.info("Operation queue processor started")
    
    def stop(self):
        """Stop the background worker"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logging.info("Operation queue processor stopped")
    
    def _process_queue(self):
        """Main processing loop"""
        while self.running:
            try:
                db = SessionLocal()
                
                # Get next pending operation
                operation = db.query(Operation).filter_by(status='pending').order_by(Operation.created_at.asc()).first()
                
                if operation:
                    logging.info(f"Processing operation {operation.operation_id} for {operation.username} ({operation.platform})")
                    self._process_operation(operation, db)
                else:
                    # No pending operations, wait a bit
                    time.sleep(self.processing_interval)
                
                db.close()
                
            except Exception as e:
                logging.error(f"Error in queue processor: {e}")
                time.sleep(self.processing_interval)
    
    def _process_operation(self, operation: Operation, db):
        """Process a single operation"""
        driver = None
        
        try:
            # Update status to processing
            operation.status = 'processing'
            operation.started_at = datetime.utcnow()
            db.commit()
            
            # Get or create account
            account = db.query(Account).filter_by(url=operation.account_url).first()
            
            if not account:
                account = Account(
                    url=operation.account_url,
                    platform=operation.platform,
                    username=operation.username,
                    status='active'
                )
                db.add(account)
                db.commit()
                db.refresh(account)
            
            operation.account_id = account.id
            db.commit()
            
            # Get scraper config
            scraper_config = config.get_default_config()
            max_scrolls = scraper_config['max_scrolls'].get(operation.platform, 20)
            limited_scrolls = min(5, max_scrolls)  # Limit to ~5 posts
            
            # Scrape videos
            video_links = []
            
            if operation.platform == 'youtube':
                video_links = youtube_scraper_recent(
                    None, operation.account_url, scraper_config['youtube_cookies'], max_videos=5
                )
            else:
                driver = self.scraper.create_driver()
                
                if operation.platform == 'instagram':
                    video_links = instagram_scraper_recent(
                        driver, operation.account_url, scraper_config['unified_cookies'], limited_scrolls
                    )
                elif operation.platform == 'tiktok':
                    video_links = tiktok_scraper_recent(
                        driver, operation.account_url, scraper_config['unified_cookies'], limited_scrolls
                    )
                elif operation.platform == 'x':
                    video_links = x_scraper_recent(
                        driver, operation.account_url, scraper_config['unified_cookies'], limited_scrolls
                    )
                elif operation.platform == 'facebook':
                    video_links = facebook_scraper_recent(
                        driver, operation.account_url, scraper_config['facebook_cookies'], limited_scrolls
                    )
            
            # Limit to exactly 5 posts
            video_links = video_links[:5]
            
            # Save new video links to database
            saved_links = []
            
            for video_url in video_links:
                # Create hash for duplicate detection
                url_hash = hashlib.sha256(video_url.encode()).hexdigest()
                
                # Check if link already exists
                existing_link = db.query(VideoLink).filter_by(
                    account_id=account.id, url_hash=url_hash
                ).first()
                
                if not existing_link:
                    # Add new video link
                    video_link = VideoLink(
                        account_id=account.id,
                        url=video_url,
                        url_hash=url_hash
                    )
                    db.add(video_link)
                
                saved_links.append(video_url)
            
            # Update account status
            account.last_checked = datetime.utcnow()
            account.last_error = None
            account.status = 'active'
            
            # Update operation with results
            operation.status = 'completed'
            operation.completed_at = datetime.utcnow()
            operation.result_links = saved_links
            operation.error_message = None
            
            db.commit()
            
            logging.info(f"Operation {operation.operation_id} completed: {len(saved_links)} videos found")
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error processing operation {operation.operation_id}: {error_msg}")
            
            # Update operation with error
            operation.status = 'failed'
            operation.completed_at = datetime.utcnow()
            operation.error_message = error_msg
            operation.result_links = []
            
            # Update account error if account exists
            try:
                if operation.account_id:
                    account = db.query(Account).filter_by(id=operation.account_id).first()
                    if account:
                        account.last_error = error_msg
                        account.status = 'error'
                        account.last_checked = datetime.utcnow()
            except:
                pass
            
            db.commit()
            
        finally:
            # Cleanup driver
            if driver:
                try:
                    driver.quit()
                except:
                    pass


# Initialize queue processor
queue_processor = OperationQueueProcessor()


@app.on_event("startup")
async def startup_event():
    """Start the queue processor on startup and resume pending operations"""
    logging.info("Starting operation queue processor...")
    queue_processor.start()
    
    # Resume any pending operations that were interrupted
    db = SessionLocal()
    try:
        pending_ops = db.query(Operation).filter_by(status='processing').all()
        for op in pending_ops:
            # Reset processing operations back to pending (they were interrupted)
            op.status = 'pending'
            op.started_at = None
            logging.info(f"Resuming interrupted operation: {op.operation_id}")
        db.commit()
        logging.info(f"Resumed {len(pending_ops)} interrupted operations")
    except Exception as e:
        logging.error(f"Error resuming operations: {e}")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the queue processor on shutdown"""
    logging.info("Stopping operation queue processor...")
    queue_processor.stop()


@app.get("/get_recent/{account_identifier:path}")
async def get_recent(account_identifier: str):
    """
    Queue a request to get recent 5 video posts from a social media account.
    Returns immediately with operation_id.
    
    Args:
        account_identifier: Full URL or username (e.g., 'instagram.com/username' or 'username')
    
    Returns:
        {
            "success": bool,
            "body": {
                "operation_id": "uuid-string"
            },
            "error": null or error message
        }
    """
    db = SessionLocal()
    
    try:
        # Normalize the account identifier to URL
        account_url, username, platform = normalize_account_url(account_identifier)
        
        if platform == 'unknown':
            db.close()
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "body": {},
                    "error": "Unsupported platform. Please provide a full URL for Instagram, TikTok, X/Twitter, Facebook, or YouTube."
                }
            )
        
        # Generate operation ID
        operation_id = str(uuid.uuid4())
        
        # Create operation record
        operation = Operation(
            operation_id=operation_id,
            account_url=account_url,
            platform=platform,
            username=username,
            status='pending'
        )
        
        db.add(operation)
        db.commit()
        
        logging.info(f"Queued operation {operation_id} for {username} ({platform})")
        
        return {
            "success": True,
            "body": {
                "operation_id": operation_id
            },
            "error": None
        }
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error queuing operation: {error_msg}")
        
        return {
            "success": False,
            "body": {},
            "error": error_msg
        }
        
    finally:
        db.close()


@app.get("/get_recent/results/{operation_id}")
async def get_results(operation_id: str):
    """
    Get the results of a queued operation.
    
    Args:
        operation_id: The operation ID returned from /get_recent/{account_identifier}
    
    Returns:
        {
            "success": bool,
            "body": {
                "status": "pending|processing|completed|failed",
                "links": [array of video links] (only if completed),
                "error": error message (only if failed)
            },
            "error": null or error message
        }
    """
    db = SessionLocal()
    
    try:
        operation = db.query(Operation).filter_by(operation_id=operation_id).first()
        
        if not operation:
            db.close()
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "body": {},
                    "error": f"Operation {operation_id} not found"
                }
            )
        
        response_body = {
            "status": operation.status,
            "operation_id": operation.operation_id,
            "account_url": operation.account_url,
            "platform": operation.platform,
            "username": operation.username
        }
        
        if operation.status == 'completed':
            response_body["links"] = operation.result_links if operation.result_links else []
        elif operation.status == 'failed':
            response_body["error"] = operation.error_message
        
        return {
            "success": True,
            "body": response_body,
            "error": None
        }
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error getting results: {error_msg}")
        
        return {
            "success": False,
            "body": {},
            "error": error_msg
        }
        
    finally:
        db.close()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Get Recent Posts API",
        "endpoints": {
            "queue": "GET /get_recent/{account_identifier} - Queue operation, returns operation_id",
            "results": "GET /get_recent/results/{operation_id} - Get operation results"
        },
        "example": {
            "queue": "/get_recent/instagram.com/username",
            "results": "/get_recent/results/{operation_id}"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
