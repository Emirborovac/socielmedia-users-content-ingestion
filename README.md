# Links Scraper v2

Enterprise-grade social media links scraper with continuous monitoring and real-time updates.

## Features

- **Multi-Platform Support**: Instagram, TikTok, X/Twitter, Facebook, YouTube
- **Continuous Monitoring**: Round-robin scheduler for automatic account checking
- **Real-Time Updates**: Automatic detection of new video posts
- **Enterprise UI**: Clean, professional interface with dark blue, white, and black theme
- **CSV Import/Export**: Bulk account management and data export
- **Duplicate Prevention**: Automatic deduplication of video links
- **Database Storage**: SQLite database for persistent data storage

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up cookies:
   - Place your cookies in `cookies/cookies.txt` (Netscape format)
   - For Facebook: `cookies/facebook.txt`
   - For YouTube: `cookies/youtube.txt`

3. Run the application:
```bash
python app.py
```

4. Access the web interface at `http://localhost:2020`

## Usage

### Adding Accounts

1. **Single Account**: Go to "Add Account" page and enter a social media URL
2. **Bulk Upload**: Upload a CSV file with account URLs

### Managing Accounts

- View all accounts on the "Accounts" page
- Toggle account status (active/paused)
- Delete accounts
- Filter by platform, status, or search

### Viewing Links

- Click "Links" button for any account to view collected video links
- Export links to CSV for external analysis
- Pagination support for large datasets

### Scheduler

- Automatically monitors active accounts in round-robin fashion
- Configurable interval between checks
- Start/stop scheduler from dashboard
- Real-time status updates

## Configuration

Edit `config.py` to customize:

- Browser settings (headless mode, Chrome version)
- Platform-specific limits (max scrolls per check)
- Scheduler interval
- Database settings

## Supported Platforms

- **Instagram**: Reels and video posts
- **TikTok**: User profile videos  
- **X/Twitter**: Video tweets
- **Facebook**: Page videos
- **YouTube**: Channel videos

## Architecture

- **Flask Backend**: RESTful API with SQLAlchemy ORM
- **SQLite Database**: Accounts and video links storage
- **Selenium WebDriver**: Browser automation for scraping
- **Round-Robin Scheduler**: Background thread for continuous monitoring
- **Bootstrap Frontend**: Responsive enterprise UI

## API Endpoints

- `GET /api/accounts` - List all accounts
- `POST /api/accounts` - Add single account
- `POST /api/accounts/bulk` - Bulk add accounts
- `GET /api/accounts/{id}/links` - Get account video links
- `GET /api/accounts/{id}/links/export` - Export links to CSV
- `POST /api/scheduler/start` - Start scheduler
- `POST /api/scheduler/stop` - Stop scheduler

## License

Enterprise Software - All Rights Reserved
