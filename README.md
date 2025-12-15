# Social Media Content Ingestion API

Professional-grade social media links scraper API with asynchronous queue processing and multi-platform support.

## Features

- **Multi-Platform Support**: Instagram, TikTok, X/Twitter, Facebook, YouTube, Telegram
- **Asynchronous Processing**: Queue-based system for handling multiple scraping operations
- **Smart Cookie Management**: Automatic cookie rotation and failure tracking (burns cookies after 3 failed attempts)
- **Modern Scraping**: Uses Playwright for browser automation and yt-dlp for video platforms
- **Proxy Support**: Built-in proxy configuration for all platforms
- **Flexible Configuration**: Environment-based settings via `.env` file
- **RESTful API**: FastAPI-based endpoints with operation tracking
- **Database Storage**: SQLite database for persistent operation history

## Supported Platforms

| Platform | Method | Cookie Required | Proxy Support |
|----------|--------|-----------------|---------------|
| Instagram | Playwright | ✅ Yes | ✅ Yes |
| TikTok | yt-dlp | ❌ No | ✅ Yes |
| X/Twitter | Playwright | ✅ Yes | ✅ Yes |
| Facebook | Playwright | ✅ Yes | ✅ Yes |
| YouTube | yt-dlp | ❌ No | ✅ Yes |
| Telegram | Telethon | ✅ Session | ⚠️ N/A |

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```env
HEADLESS=FALSE
PROXY=http://username:password@proxy.example.com:10000
```

- `HEADLESS`: Set to `TRUE` for headless browser mode, `FALSE` to see the browser
- `PROXY`: Optional HTTP proxy URL (used for TikTok and YouTube)

### 4. Set Up Cookies

Organize cookies in the following folder structure:

```
cookies/
├── instagram/
│   ├── active/
│   │   └── 1.txt
│   └── burnt/
├── facebook/
│   ├── active/
│   │   └── facebook.txt
│   └── burnt/
├── x/
│   ├── active/
│   │   └── x.txt
│   └── burnt/
├── tiktok/
│   ├── active/
│   └── burnt/
└── youtube/
    ├── active/
    │   └── youtube.txt
    └── burnt/
```

**Cookie format**: Netscape/Mozilla format (can be exported from browser extensions like "Get cookies.txt")

### 5. Set Up Telegram (Optional)

If you want to scrape Telegram channels, run the setup script once:

```bash
python setup_telegram.py
```

This will:
- Prompt for your phone number
- Send a verification code
- Create a `tg_recent_posts.session` file for future use

**Required**: Add your Telegram API credentials to `config.py`:
```python
TELEGRAM_API_ID = "your_api_id"
TELEGRAM_API_HASH = "your_api_hash"
```

Get these from: https://my.telegram.org/apps

### 6. Run the Application

```bash
python get_recent.py
```

The API will be available at: `http://localhost:8000`

## API Usage

### 1. Submit a Scraping Request

**Endpoint**: `GET /get_recent/{account_identifier:path}`

**Parameters**:
- `account_identifier`: Social media profile URL or identifier
- `type` (YouTube only): `videos` or `shorts` (default: `shorts`)

**Examples**:

```bash
# Instagram
curl http://localhost:8000/get_recent/instagram.com/cristiano

# TikTok
curl http://localhost:8000/get_recent/tiktok.com/@rozi_star2

# X/Twitter
curl http://localhost:8000/get_recent/twitter.com/elonmusk

# Facebook
curl http://localhost:8000/get_recent/facebook.com/zuck

# YouTube - Videos
curl "http://localhost:8000/get_recent/youtube.com/@MrBeast?type=videos"

# YouTube - Shorts (default)
curl http://localhost:8000/get_recent/youtube.com/@MrBeast/shorts

# Telegram
curl http://localhost:8000/get_recent/t.me/durov
```

**Response**:
```json
{
  "success": true,
  "body": {
    "operation_id": "abc-123-def-456"
  },
  "error": null
}
```

### 2. Check Operation Results

**Endpoint**: `GET /get_recent/results/{operation_id}`

```bash
curl http://localhost:8000/get_recent/results/abc-123-def-456
```

**Response (Processing)**:
```json
{
  "success": false,
  "body": {
    "operation_id": "abc-123-def-456",
    "status": "processing",
    "url": "https://instagram.com/cristiano"
  },
  "error": "Operation is processing, not yet completed"
}
```

**Response (Completed)**:
```json
{
  "success": true,
  "body": {
    "status": "completed",
    "operation_id": "abc-123-def-456",
    "account_url": "https://instagram.com/cristiano",
    "platform": "instagram",
    "username": "cristiano",
    "links": [
      "https://www.instagram.com/p/ABC123/",
      "https://www.instagram.com/reel/DEF456/",
      "https://www.instagram.com/p/GHI789/",
      "https://www.instagram.com/p/JKL012/",
      "https://www.instagram.com/reel/MNO345/"
    ]
  },
  "error": null
}
```

**Response (Failed)**:
```json
{
  "success": false,
  "body": null,
  "error": "Failed to scrape account: Timeout"
}
```

### 3. Typical Workflow

```bash
# Step 1: Submit request
OPERATION_ID=$(curl -s http://localhost:8000/get_recent/instagram.com/cristiano | jq -r '.body.operation_id')

# Step 2: Wait a few seconds
sleep 5

# Step 3: Get results
curl http://localhost:8000/get_recent/results/$OPERATION_ID
```

## How It Works

### Queue-Based Processing

1. **Request Submission**: Client submits a scraping request via API
2. **Operation Creation**: System creates an operation record in the database
3. **Queue Addition**: Operation is added to an async processing queue
4. **Background Processing**: Worker threads process operations sequentially
5. **Result Storage**: Results are saved to the database
6. **Result Retrieval**: Client polls for results using the operation ID

### Cookie Management

- Cookies are stored per-platform in `cookies/{platform}/active/` folders
- The system tracks failures for each cookie
- After **3 failed scraping attempts**, the cookie is automatically moved to `cookies/{platform}/burnt/`
- The next available cookie is used for subsequent requests
- Successful operations reset the failure count

### Smart Scraping

**Instagram, Facebook, X/Twitter (Playwright)**:
- Loads cookies into browser context
- Navigates to profile page
- Scrolls to load posts
- Extracts post links with intelligent filtering
- Skips pinned posts, stories, and non-owner content

**TikTok, YouTube (yt-dlp)**:
- Uses yt-dlp to extract video information
- No browser needed (faster and more reliable)
- Supports proxy configuration
- Returns up to 5 recent posts

**Telegram (Telethon)**:
- Uses Telegram API via Telethon client
- Requires one-time authentication setup
- Fetches recent channel messages
- No browser or cookies needed

## Configuration

Edit `config.py` to customize:

```python
# Browser settings
HEADLESS_MODE = os.getenv('HEADLESS', 'TRUE').upper() == 'TRUE'
PROXY = os.getenv('PROXY', None)

# Cookie paths
COOKIES = {
    'instagram': {
        'active': './cookies/instagram/active',
        'burnt': './cookies/instagram/burnt'
    },
    # ... other platforms
}

# Telegram API credentials
TELEGRAM_API_ID = "your_api_id"
TELEGRAM_API_HASH = "your_api_hash"
```

## Architecture

- **FastAPI Backend**: Modern async web framework
- **SQLite Database**: Operation history and status tracking
- **Playwright**: Browser automation for Instagram, Facebook, X/Twitter
- **yt-dlp**: Video platform scraping for TikTok, YouTube
- **Telethon**: Telegram API client
- **Async Queue**: Background job processing with asyncio
- **Cookie Manager**: Smart cookie rotation and failure tracking

## Troubleshooting

### Browser Not Opening (HEADLESS=FALSE not working)

Make sure your `.env` file is UTF-8 encoded without BOM. Recreate it:
```bash
echo HEADLESS=FALSE > .env
echo PROXY=your_proxy_url >> .env
```

### Cookie Not Found Errors

Check:
1. Cookie files exist in `cookies/{platform}/active/` folder
2. Cookie files are in Netscape format
3. Cookies haven't expired (login again if needed)

### Telegram Login Issues

1. Run `python setup_telegram.py` to authenticate
2. Make sure API ID and Hash are set in `config.py`
3. Check that `tg_recent_posts.session` file was created

### Playwright Browser Issues

Reinstall browsers:
```bash
playwright install --force chromium
```

## Requirements

- Python 3.8+
- Chrome/Chromium (for Playwright)
- Valid social media cookies (for platforms that require authentication)
- Telegram API credentials (for Telegram scraping)

## License

All Rights Reserved
